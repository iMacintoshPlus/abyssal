# *Abyssal* Compatibility Engine

An iOS build forked from [TheWWWorm's independent Godot engine for *DEEP: Submarine Odyssey*](https://github.com/TheWWWorm/abyssal). 

Abyssal reads a *DEEP* JAR you already own and converts it on your own device. Submarine flight, stations, trading, missions and combat run natively, with modern lighting, a readable interface, and a world map with autopilot.

> **You need your own copy of *DEEP*.** No game data ships with this engine - no models, textures, music, sound or interface art. Nothing is downloaded for you. Without your own JAR there is nothing to play.

For more information, please refer to the original [README](https://github.com/TheWWWorm/abyssal/blob/main/README.md).

## Screenshots

[![The submarine running in towards Rygg under its own headlights, two vessels coming out from the station under theirs](docs/screenshots/headlights-off-rygg.jpg)](https://github.com/TheWWWorm/abyssal/releases/download/v1.0.0/abyssal-engine-1.0.0-screenshot-headlights-off-rygg.png)

[![Rygg station from outside, the submarine crossing in front of it](docs/screenshots/rygg-from-outside.jpg)](https://github.com/TheWWWorm/abyssal/releases/download/v1.0.0/abyssal-engine-1.0.0-screenshot-rygg-from-outside.png)

[![The engine module of a station, its rotor turning under the work lamps, lit by the submarine's headlights](docs/screenshots/station-engine.jpg)](https://github.com/TheWWWorm/abyssal/releases/download/v1.0.0/abyssal-engine-1.0.0-screenshot-station-engine.png)

[![The submarine leaving a station's berth, its beams out ahead of it](docs/screenshots/leaving-the-berth.jpg)](https://github.com/TheWWWorm/abyssal/releases/download/v1.0.0/abyssal-engine-1.0.0-screenshot-leaving-the-berth.png)

[![A S.T.R.E.A.M. gate opening in front of the submarine](docs/screenshots/stream-gate.jpg)](https://github.com/TheWWWorm/abyssal/releases/download/v1.0.0/abyssal-engine-1.0.0-screenshot-stream-gate.png)

[A one-minute trailer in 4K](https://github.com/TheWWWorm/abyssal/releases/download/v1.0.0/abyssal-engine-1.0.0-trailer-4k.mp4) - stations from outside and in, a departure, a fight, the gate - rendered by the engine itself from a converted copy of the game.

## Install and Play

**Download the latest IPA from [here](https://github.com/iMacintoshPlus/galaxian/releases/latest) and install using your preferred sideloading method. AltStore/SideStore/LiveContainer users can add `https://raw.githubusercontent.com/iMacintoshPlus/altstore-source/main/source.json` as a source.**

| Platform | Download | Start |
| --- | --- | --- |
| iOS 14.0+ | `Abyssal-iOS-unsigned.ipa` | Sideload the IPA, then open `Abyssal`. |

1. Launch the application.
2. Choose your *DEEP* JAR when asked; its filename does not matter.
3. Wait for the first conversion to finish before closing the app.

The app was compiled with the iOS 26.2 SDK and supports 14.0 and later, but compatibility is only currently verified on 18.7.8 (iPhone 14 Pro). It uses the native Metal renderer (with OpenGL ES 3 as a fallback) and requests no network or broad storage permissions. Later IPA updates preserve content and saves; uninstalling removes them.

You do not need Godot, Python, Java, Node.js or a compiler, and the bundled converter runs completely offline. Choose your JAR from the system file picker and keep the app open until conversion finishes. Your JAR never leaves your device. The game remembers imported content and station checkpoints in your user storage, so you only import once.

### Which DEEP Builds Work?

The engine is developed against the **Sony Ericsson release of DEEP 1.0.8**, identified by SHA-256: `a247f8a872dda268ed8138086bd0de6d038d7faf7ef31469b0efe3eb54209d26`

That is the build all gameplay checking is done on. It is not a requirement. Any DEEP MIDlet JAR is accepted, and the importer converts it whenever the build stores its data the way the engine expects. Localised builds are supported: the language shipped in the JAR is the language you play in.

The engine's own menus, settings and messages follow the game's language when the engine has it, and otherwise the system language. Settings → Display → Language picks one by hand. The engine text is available in English, Russian, Ukrainian, German, French, Spanish, Brazilian Portuguese, Italian, Polish, Turkish, Indonesian, Vietnamese, Simplified Chinese, Japanese and Korean. The story, ship and item names always come from the JAR.

To change the story's language, choose a JAR in that language with matching game data. Existing saves stay loadable when only the text differs; see the save compatibility details below. **Transfer save** exports a backup to keep separately.

| Build | Result |
| --- | --- |
| Sony Ericsson 1.0.8 (English) | Developed and validated against this build. |
| Sony Ericsson 1.0.3 (Russian) | Converts; the engine check suite passes on it, and the game is in Russian. |
| "Deep 3D: Submarine Odyssey (Mascot3D)" 1.0.8, Fishlabs manifest | Converts. It is the same build as the Sony Ericsson release apart from its manifest, but the circulating copy is repacked with its last entry a byte short, which stock ZIP readers refuse. The importer recovers the entry, checks its size and CRC, and produces identical content. |
| "Deep 3D Submarine Odyssey" 1.0.8 with `data/3d/*.m3g` | Does not convert, and says so. This is the JSR-184 (M3G) edition of the game: its models are in a different format from the Mascot Capsule (MBAC) builds the engine decodes. |
| Nokia 1.0.3 | Does not convert; its code differs in ways the restricted data reader does not cover. |

If a build does not match, import stops with a message naming what did not fit, rather than producing a broken game.

## Modding

Nothing is shipped as a mod; the game reads a `mods` folder you make yourself, and whatever it finds there stands in for the imported art or music. Collision, aim and the camera keep the imported models' extents, so a mod changes the look and sound, not the game.

**Where the Folder Goes:** In the user data folder, which can be accessed through the **Mods** page on the title screen or the Files app. iOS uses private application storage; uninstalling the app removes that storage.

**Textures (From the Title Menu):** **Mods → Textures** on the title screen lists the two atlases the game is drawn from, each shown as painted and as the see-through polygons see it, with what stands for it now and **View**, **Replace…** (a PNG from your device, through the system file picker) and **Restore original**. A replacement applies at once. Everything below is the same thing done by hand.

**Textures:** Put a PNG at `mods/textures/deep.png` or `mods/textures/fx.png` to replace that atlas (a `.bmp` works too). `deep` carries the submarines, stations, mines, torpedoes, boxes and the gate; `fx` the creatures, algae, shots, explosions and effects. Any size works: a 4x or 8x repaint is drawn at more pixels per texel, but keep the original's layout, because every model addresses the atlas by the original's texel positions. One file does both kinds of polygon: where the original sees through a polygon its atlas is pure white - the phone's transparent palette colour - and the engine keys pure white (or your PNG's own transparency) out on those polygons itself, so leave see-through areas white or transparent and use no pure white elsewhere. The originals to paint over are `deep.bmp.png` and `fx.bmp.png` in your content cache (`user data folder/content/<hash>/data/textures/`, or **Open original textures** on the Mods page). The skybox atlas is not offered: this engine does not draw it - the water is its own sky, and only one texel of the original's skybox tints the shallows.

**Music (From the Title Menu):** **Mods → Music** lists the JAR's two tracks - `intro` (the menu and a new game's opening) and `station` (docked) - with what plays for each now and its length, and **Listen**, **Replace…** (an OGG Vorbis, MP3 or WAV file, through the system file picker) and **Restore original**. A replacement plays at once, looped from start to end, wherever the converted MIDI would have played. Done by hand, put the file at `mods/music/intro.ogg` or `mods/music/station.ogg` (`.mp3` or `.wav` work too; the file's content decides its format, not its extension). A 1.0.8 JAR has no intro track; a replacement adds one, which plays when **Settings → Audio → Menu and opening music** is set to **Intro**. The converted originals are `intro.mid.wav` and `station.mid.wav` in `user data folder/content/<hash>/data/sound/`. Files up to 64 MiB are accepted.

**Models:** Put a glTF at `mods/models/<name>.glb` (or `.gltf`) to replace the model of that name. The model is scaled uniformly to the imported model's longest extent and centred on it, so orient it the way the original faces in the content inspector on the title screen. If the file carries animations, the first one loops; the imported skeletal poses are not applied. The names:

- Submarines: `u0` to `u10`, in dealer order.
- Stations: `station_hangar_ve`, `station_hangar_de` (the two hangar roots), `station_habitat_ve`, `station_habitat_de`, `station_sidehabitat`, `station_starter`, `station_top`, `station_bottom`, `station_engine`, `station_bridge_01`, `station_bridge_02`, `station_cannon`.
- Creatures: `shark_01`, `shark_02`, `whale_01`, `whale_02`, `marlin_01`, `marlin_02`, `devilfish_01`, `devilfish_02`, `anglerfish_01`, `anglerfish_02`, `squid_01`, `squid_02`, `shrimp_01`, `shrimp_02`, `turtle_01`, `turtle_02`, `gulper_eel`, `jellyfish`, `manta`, `nautilus`, `fish_swarm`, `alga_blue`, `alga_brown`, `alga_gold`, `alga_green`, `alga_red`.
- Vessels and objects: `tanker1`, `aquar`, `kapsel`, `box`, `biowaste`, `trash`, `mine`, `torpedo`, `pfeil` (the harpoon), `laser_0` to `laser_11` and `laser_aqua` (the shots), `explosion`, `fischtod`, `eclipse`, `limiter_up`, `limiter_down`, `stream` (the gate), `skybox`.

Replacements are read when the game starts, so restart after adding or changing a file. Distant streamed stations keep the imported models until you are close. A file the game cannot read is reported once in the log and the imported model is used instead.

## Notices

This project is an unofficial fork containing AI-assisted changes and is not affiliated with or endorsed by [TheWWWorm](https://github.com/TheWWWorm). Please direct all donations to [ko-fi.com/wwworm](https://ko-fi.com/wwworm).

The importer recognizes compatible JAR structure, computes a SHA-256 identity for isolated caches, then decodes its resource entries and reads class-file data tables with a **restricted bytecode evaluator**. That evaluator reads literal assignments, arrays, arithmetic and bounded control flow, resolving calls only through explicit inert data summaries; unsupported opcodes fail. It never loads or invokes original classes in a JVM, and no original bytecode or method body is written to its output. It does, however, inspect and evaluate parts of original method bodies. Because some content is derived that way, this is reverse engineering and **not** a clean-room reimplementation. Decoded models, textures, audio, catalogue rows and narrative records exist only in your own local cache - none are distributed here.

This engine's own source is licensed under the [Apache License 2.0](LICENSE.md). That covers the code in this repository and nothing else. It grants you no rights to the original DEEP game, its JAR, its class files or anything converted from them; those are not this project's to license and are not distributed here. The three vendored decoder files keep their own Apache-2.0 notices, listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Content you convert is private. Do not redistribute it with the engine, and never share the JAR, a converted pack or a conversion cache. The name is a working title, not a trademark claim. Menus and instrument frames are drawn in code; original logos, portraits and icons are loaded locally from your own import.
