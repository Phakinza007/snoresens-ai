import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    guard let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "SnoresensFiles") else { return }
    let channel = FlutterMethodChannel(name: "snoresens/files", binaryMessenger: registrar.messenger())
    channel.setMethodCallHandler { call, result in
      guard call.method == "protect", let args = call.arguments as? [String: Any],
            let path = args["path"] as? String else { result(FlutterMethodNotImplemented); return }
      let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].resolvingSymlinksInPath().path
      let file = URL(fileURLWithPath: path).resolvingSymlinksInPath().path
      guard file.hasPrefix(documents + "/") else { result(FlutterError(code: "path", message: "Invalid application file", details: nil)); return }
      do {
        try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: file)
        result(nil)
      } catch { result(FlutterError(code: "protection", message: error.localizedDescription, details: nil)) }
    }
  }
}
