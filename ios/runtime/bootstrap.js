/* Offline iOS bridge. The selected JAR and converted pack stay on this device. */
'use strict';
(function (scope) {
  const send = (type, value) => scope.webkit.messageHandlers.abyssal.postMessage({type, value: value || ''});
  const status = document.getElementById('status');
  scope.AbyssalNative = {
    progress: message => { status.textContent = message; send('progress', message); },
    begin: () => send('begin'), chunk: data => send('chunk', data),
    complete: () => send('complete'), failed: message => send('failed', message)
  };
  // Match the compatibility runtime already shipped for Android WebViews so
  // the import path also works on the older WKWebKit versions in iOS 14.
  scope.AbyssalImporterRuntime = {indexURL: new URL('vendor-compat/', scope.location.href).href};
  document.getElementById('cancel').addEventListener('click', () => send('cancel'));
  function load(path, check) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script'); script.src = path;
      script.onload = () => check() ? resolve() : reject(new Error('Importer script did not initialize: ' + path));
      script.onerror = () => reject(new Error('Could not load the bundled importer: ' + path));
      document.head.appendChild(script);
    });
  }
  (async () => {
    try {
      scope.AbyssalNative.progress('Loading the offline DEEP importer…');
      await load('vendor-compat/pyodide.js', () => typeof scope.loadPyodide === 'function');
      await load('vendor/amrnb.js', () => scope.AMR && typeof scope.AMR.toWAV === 'function');
      await load('audio.js', () => scope.AbyssalAudio && typeof scope.AbyssalAudio.midiWav === 'function');
      await load('import.js', () => true);
    } catch (error) {
      scope.AbyssalNative.failed(String(error.message || error));
    }
  })();
})(window);
