// iOS document picker and offline WebKit bridge for the shared JAR importer.
#import <UIKit/UIKit.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#import <WebKit/WebKit.h>
#import <TargetConditionals.h>
#include "core/config/engine.h"
#include "core/io/file_access.h"
#include "core/object/class_db.h"

class AbyssalIOSImporter;
static AbyssalIOSImporter *plugin = nullptr;

@interface AbyssalDocumentDelegate : NSObject <UIDocumentPickerDelegate>
@property(nonatomic, weak) UIViewController *pickerPresenter;
@end

@interface AbyssalWebBridge : NSObject <WKScriptMessageHandler, WKURLSchemeHandler, WKNavigationDelegate>
@property(nonatomic, assign) AbyssalIOSImporter *owner;
@property(nonatomic, strong) WKWebView *webView;
@property(nonatomic, strong) UIViewController *webController;
@property(nonatomic, strong) NSURL *inputURL;
@property(nonatomic, strong) NSData *jarData;
@property(nonatomic, strong) NSDictionary<NSString *, NSData *> *resources;
@property(nonatomic, strong) NSURL *outputURL;
@property(nonatomic, strong) NSFileHandle *output;
@property(nonatomic, assign) unsigned long long written;
@property(nonatomic, assign) unsigned long long generation;
- (void)closeWebView:(void (^)(void))completion;
@end

static AbyssalDocumentDelegate *document_delegate = nil;
static AbyssalWebBridge *web_bridge = nil;

class AbyssalIOSImporter : public Object {
    GDCLASS(AbyssalIOSImporter, Object);
    bool busy = false;
protected:
    static void _bind_methods() {
        ClassDB::bind_method(D_METHOD("choose"), &AbyssalIOSImporter::choose);
        ClassDB::bind_method(D_METHOD("cancel"), &AbyssalIOSImporter::cancel);
        ClassDB::bind_method(D_METHOD("is_simulator"), &AbyssalIOSImporter::is_simulator);
        ADD_SIGNAL(MethodInfo("selected", PropertyInfo(Variant::STRING, "path")));
        ADD_SIGNAL(MethodInfo("failed", PropertyInfo(Variant::STRING, "message")));
        ADD_SIGNAL(MethodInfo("progress", PropertyInfo(Variant::STRING, "message")));
        ADD_SIGNAL(MethodInfo("busy_changed", PropertyInfo(Variant::BOOL, "active")));
    }
public:
    bool is_simulator() const { return TARGET_OS_SIMULATOR; }
    void emit(const char *signal, const Variant &value) { emit_signal(signal, value); }
    bool is_busy() const { return busy; }
    void set_busy(bool value) {
        if (busy == value) return;
        busy = value;
        emit_signal("busy_changed", value);
    }
    void fail(const char *message) {
        set_busy(false);
        emit("failed", String::utf8(message));
    }
    void choose();
    void cancel();
};

static UIViewController *presenter() {
    for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
        if (scene.activationState != UISceneActivationStateForegroundActive ||
            ![scene isKindOfClass:UIWindowScene.class]) continue;
        for (UIWindow *window in ((UIWindowScene *)scene).windows) {
            if (!window.isKeyWindow) continue;
            UIViewController *view = window.rootViewController;
            while (view.presentedViewController) view = view.presentedViewController;
            return view;
        }
    }
    return nil;
}

static void remove_import_files(AbyssalWebBridge *bridge) {
    if (bridge.output) { [bridge.output closeFile]; bridge.output = nil; }
    if (bridge.inputURL) { [NSFileManager.defaultManager removeItemAtURL:bridge.inputURL error:nil]; bridge.inputURL = nil; }
    if (bridge.outputURL) { [NSFileManager.defaultManager removeItemAtURL:bridge.outputURL error:nil]; bridge.outputURL = nil; }
    bridge.jarData = nil;
    bridge.resources = nil;
}

static NSDictionary<NSString *, NSData *> *load_importer_resources() {
    NSArray<NSString *> *paths = @[
        @"index.html", @"bootstrap.js", @"import.js", @"audio.js", @"sources.zip",
        @"vendor/amrnb.js", @"vendor-compat/pyodide.js", @"vendor-compat/pyodide.asm.js",
        @"vendor-compat/pyodide.asm.wasm", @"vendor-compat/pyodide.asm.data",
        @"vendor-compat/pyodide_py.tar", @"vendor-compat/packages.json"
    ];
    NSMutableDictionary<NSString *, NSData *> *resources = [NSMutableDictionary dictionary];
    for (NSString *path in paths) {
        String resource = String("res://ios_importer/") + String::utf8(path.UTF8String);
        Ref<FileAccess> file = FileAccess::open(resource, FileAccess::READ);
        if (file.is_null()) continue;
        PackedByteArray bytes = file->get_buffer(file->get_length());
        resources[path] = [NSData dataWithBytes:bytes.ptr() length:bytes.size()];
    }
    for (NSString *required in @[@"index.html", @"bootstrap.js", @"import.js", @"audio.js",
            @"sources.zip", @"vendor/amrnb.js", @"vendor-compat/pyodide.js",
            @"vendor-compat/pyodide.asm.js", @"vendor-compat/pyodide.asm.wasm",
            @"vendor-compat/pyodide.asm.data", @"vendor-compat/pyodide_py.tar"]) {
        if (!resources[required]) return nil;
    }
    return resources;
}

void AbyssalIOSImporter::choose() {
    if (busy) { cancel(); return; }
    UIViewController *view = presenter();
    if (!view || view.isBeingDismissed) { fail("The file picker cannot open right now. Try again."); return; }
    [web_bridge setGeneration:web_bridge.generation + 1];
    remove_import_files(web_bridge);
    UIDocumentPickerViewController *picker = [[UIDocumentPickerViewController alloc]
        initForOpeningContentTypes:@[UTTypeData] asCopy:YES];
    picker.allowsMultipleSelection = NO;
    picker.delegate = document_delegate;
    document_delegate.pickerPresenter = view;
    set_busy(true);
    [view presentViewController:picker animated:YES completion:nil];
}

void AbyssalIOSImporter::cancel() {
    dispatch_async(dispatch_get_main_queue(), ^{
        if (!plugin || !plugin->is_busy()) return;
        web_bridge.generation++;
        [web_bridge closeWebView:nil];
        remove_import_files(web_bridge);
        plugin->set_busy(false);
        plugin->emit("failed", String("Import cancelled."));
    });
}

@implementation AbyssalDocumentDelegate
- (void)documentPicker:(UIDocumentPickerViewController *)controller didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
    if (!plugin) return;
    if (urls.count == 0) { plugin->set_busy(false); return; }
    NSURL *url = urls.firstObject;
    BOOL access = [url startAccessingSecurityScopedResource];
    NSString *extension = url.pathExtension.lowercaseString;
    BOOL isPack = [extension isEqualToString:@"abyss"];
    BOOL isJar = [extension isEqualToString:@"jar"];
    NSNumber *size = nil;
    NSError *error = nil;
    BOOL valid = (isJar || isPack) && [url getResourceValue:&size forKey:NSURLFileSizeKey error:&error] &&
        size.unsignedLongLongValue <= (isJar ? 16ULL : 128ULL) * 1024ULL * 1024ULL;
    if (!valid) {
        if (access) [url stopAccessingSecurityScopedResource];
        plugin->set_busy(false);
        plugin->fail("Choose a DEEP .jar under 16 MiB or an .abyss content pack under 128 MiB.");
        return;
    }
    NSString *name = [NSString stringWithFormat:@"abyssal-input-%@.%@", NSUUID.UUID.UUIDString, extension];
    NSURL *destination = [NSURL fileURLWithPath:[NSTemporaryDirectory() stringByAppendingPathComponent:name]];
    BOOL copied = [NSFileManager.defaultManager copyItemAtURL:url toURL:destination error:&error];
    if (access) [url stopAccessingSecurityScopedResource];
    if (!copied) {
        plugin->set_busy(false);
        plugin->fail("Could not copy the selected file into app storage.");
        return;
    }
    if (isPack) {
        plugin->set_busy(false);
        plugin->emit("selected", String::utf8(destination.path.UTF8String));
        [NSFileManager.defaultManager removeItemAtURL:destination error:nil];
        return;
    }
    web_bridge.inputURL = destination;
    web_bridge.jarData = [NSData dataWithContentsOfURL:destination options:NSDataReadingMappedIfSafe error:&error];
    web_bridge.resources = load_importer_resources();
    if (!web_bridge.jarData || !web_bridge.resources) {
        remove_import_files(web_bridge);
        plugin->fail("Could not read the bundled offline importer files.");
        return;
    }
    plugin->emit("progress", String("Starting the offline DEEP importer…"));
    // UIKit may call this delegate before its document picker dismissal has
    // completed. Wait for that completion before presenting the web importer;
    // dispatching one main-loop turn is not enough to finish the transition.
    UIViewController *pickerPresenter = controller.presentingViewController ?: document_delegate.pickerPresenter;
    void (^presentImporter)(void) = ^{
        if (!plugin || !plugin->is_busy()) return;
        UIViewController *view = pickerPresenter;
        if (!view || view.isBeingDismissed || view.presentedViewController) {
            remove_import_files(web_bridge); plugin->fail("The offline importer could not open."); return;
        }
        WKWebViewConfiguration *configuration = [WKWebViewConfiguration new];
        configuration.websiteDataStore = WKWebsiteDataStore.nonPersistentDataStore;
        [configuration setURLSchemeHandler:web_bridge forURLScheme:@"abyssal"];
        [configuration.userContentController addScriptMessageHandler:web_bridge name:@"abyssal"];
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = NO;
        web_bridge.webView = [[WKWebView alloc] initWithFrame:view.view.bounds configuration:configuration];
        web_bridge.webView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        web_bridge.webView.navigationDelegate = web_bridge;
        web_bridge.webView.allowsBackForwardNavigationGestures = NO;
        web_bridge.webView.scrollView.bounces = NO;
        web_bridge.generation++;
        web_bridge.webController = [UIViewController new];
        web_bridge.webController.modalPresentationStyle = UIModalPresentationFullScreen;
        web_bridge.webController.view = web_bridge.webView;
        [view presentViewController:web_bridge.webController animated:NO completion:^{
            [web_bridge.webView loadRequest:[NSURLRequest requestWithURL:[NSURL URLWithString:@"abyssal://local/index.html"]]];
        }];
    };
    if (controller.presentingViewController) {
        [controller dismissViewControllerAnimated:NO completion:presentImporter];
    } else {
        dispatch_async(dispatch_get_main_queue(), presentImporter);
    }
}
- (void)documentPickerWasCancelled:(UIDocumentPickerViewController *)controller {
    if (plugin) { plugin->set_busy(false); plugin->emit("failed", String("Import cancelled.")); }
}
@end

@implementation AbyssalWebBridge
- (void)closeWebView:(void (^)(void))completion {
    UIViewController *controller = self.webController;
    [self.webView stopLoading];
    self.webView.navigationDelegate = nil;
    self.webView = nil;
    self.webController = nil;
    if (controller.presentingViewController && !controller.isBeingDismissed) {
        [controller dismissViewControllerAnimated:NO completion:completion];
    } else if (completion) {
        completion();
    }
}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message {
    if (!plugin || ![message.body isKindOfClass:NSDictionary.class]) return;
    NSDictionary *body = message.body;
    NSString *type = [body[@"type"] isKindOfClass:NSString.class] ? body[@"type"] : @"";
    NSString *value = [body[@"value"] isKindOfClass:NSString.class] ? body[@"value"] : @"";
    if ([type isEqualToString:@"progress"]) {
        plugin->emit("progress", String::utf8(value.UTF8String));
    } else if ([type isEqualToString:@"cancel"]) {
        plugin->cancel();
    } else if ([type isEqualToString:@"begin"]) {
        NSError *error = nil;
        self.outputURL = [NSURL fileURLWithPath:[NSTemporaryDirectory() stringByAppendingPathComponent:
            [NSString stringWithFormat:@"abyssal-output-%@.abyss", NSUUID.UUID.UUIDString]]];
        [[NSFileManager defaultManager] createFileAtPath:self.outputURL.path contents:nil attributes:nil];
        self.output = [NSFileHandle fileHandleForWritingToURL:self.outputURL error:&error];
        self.written = 0;
        if (!self.output) plugin->fail("Could not create temporary content storage.");
    } else if ([type isEqualToString:@"chunk"]) {
        if (!self.output || value.length > 400000) { plugin->fail("Invalid importer output."); return; }
        NSData *chunk = [[NSData alloc] initWithBase64EncodedString:value options:0];
        self.written += chunk.length;
        if (!chunk || self.written > 128ULL * 1024ULL * 1024ULL) { plugin->fail("Converted content exceeds 128 MiB."); return; }
        @try { [self.output writeData:chunk]; }
        @catch (NSException *exception) { plugin->fail("Could not write converted content."); }
    } else if ([type isEqualToString:@"complete"]) {
        if (!self.output || !self.outputURL) { plugin->fail("The importer produced no content pack."); return; }
        [self.output synchronizeFile]; [self.output closeFile]; self.output = nil;
        NSString *path = self.outputURL.path;
        self.outputURL = nil;
        [self closeWebView:^{
            if (self.inputURL) { [NSFileManager.defaultManager removeItemAtURL:self.inputURL error:nil]; self.inputURL = nil; }
            self.jarData = nil; self.resources = nil;
            plugin->set_busy(false);
            plugin->emit("selected", String::utf8(path.UTF8String));
            [NSFileManager.defaultManager removeItemAtPath:path error:nil];
        }];
    } else if ([type isEqualToString:@"failed"]) {
        NSString *message = value.length ? value : @"The offline importer failed.";
        [self closeWebView:^{
            remove_import_files(self);
            plugin->set_busy(false);
            plugin->emit("failed", String::utf8(message.UTF8String));
        }];
    }
}
- (void)webView:(WKWebView *)webView didStartProvisionalNavigation:(WKNavigation *)navigation {
    if (plugin) plugin->emit("progress", String("Loading the bundled offline importer…"));
}
- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    if (plugin) {
        [self closeWebView:^{ remove_import_files(self); plugin->fail("The bundled offline importer could not start."); }];
    }
}
- (void)webView:(WKWebView *)webView didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    if (plugin) {
        [self closeWebView:^{ remove_import_files(self); plugin->fail("The bundled offline importer stopped unexpectedly."); }];
    }
}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView {
    if (plugin && self.webView == webView) {
        [self closeWebView:^{
            remove_import_files(self);
            plugin->fail("iOS stopped the offline importer. Close other apps and try again.");
        }];
    }
}
- (void)webView:(WKWebView *)webView decidePolicyForNavigationAction:(WKNavigationAction *)action decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {
    NSURL *url = action.request.URL;
    decisionHandler([url.scheme isEqualToString:@"abyssal"] && [url.host isEqualToString:@"local"]
        ? WKNavigationActionPolicyAllow : WKNavigationActionPolicyCancel);
}
- (void)webView:(WKWebView *)webView startURLSchemeTask:(id<WKURLSchemeTask>)task {
    NSURL *url = task.request.URL;
    NSString *path = url.path.length > 1 ? [url.path substringFromIndex:1] : @"";
    if (![url.scheme isEqualToString:@"abyssal"] || ![url.host isEqualToString:@"local"] ||
        [path containsString:@".."] || [path containsString:@"%"] || [path containsString:@"?"]) {
        [task didFailWithError:[NSError errorWithDomain:@"AbyssalImporter" code:1 userInfo:nil]]; return;
    }
    NSData *data = [path isEqualToString:@"game.jar"] ? self.jarData : self.resources[path];
    if (!data) { [task didFailWithError:[NSError errorWithDomain:@"AbyssalImporter" code:2 userInfo:nil]]; return; }
    NSString *mime = [path hasSuffix:@".html"] ? @"text/html" :
        [path hasSuffix:@".js"] ? @"text/javascript" :
        [path hasSuffix:@".wasm"] ? @"application/wasm" :
        [path hasSuffix:@".json"] ? @"application/json" : @"application/octet-stream";
    BOOL isText = [mime hasPrefix:@"text/"] || [mime isEqualToString:@"application/json"];
    NSString *contentType = isText ? [mime stringByAppendingString:@"; charset=utf-8"] : mime;
    NSDictionary *headers = @{
        @"Content-Type": contentType,
        @"Content-Length": [NSString stringWithFormat:@"%llu", (unsigned long long)data.length],
        @"Access-Control-Allow-Origin": @"*"
    };
    // Fetch/XHR consumers (including Emscripten's WASM loader) need an HTTP
    // success status. NSURLResponse alone reports status 0 to WebKit here.
    NSHTTPURLResponse *response = [[NSHTTPURLResponse alloc] initWithURL:url statusCode:200
        HTTPVersion:@"HTTP/1.1" headerFields:headers];
    [task didReceiveResponse:response]; [task didReceiveData:data]; [task didFinish];
}
- (void)webView:(WKWebView *)webView stopURLSchemeTask:(id<WKURLSchemeTask>)task {}
@end

void abyssal_ios_importer_init() {
    ClassDB::register_class<AbyssalIOSImporter>();
    plugin = memnew(AbyssalIOSImporter);
    document_delegate = [AbyssalDocumentDelegate new];
    web_bridge = [AbyssalWebBridge new]; web_bridge.owner = plugin;
    Engine::get_singleton()->add_singleton(Engine::Singleton("AbyssalIOSImporter", plugin));
}
void abyssal_ios_importer_deinit() {
    if (web_bridge) { [web_bridge closeWebView:nil]; remove_import_files(web_bridge); }
    Engine::get_singleton()->remove_singleton("AbyssalIOSImporter");
    memdelete(plugin); plugin = nullptr; web_bridge = nil; document_delegate = nil;
}
