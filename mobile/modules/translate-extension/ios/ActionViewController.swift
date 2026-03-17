import UIKit
import MobileCoreServices
import UniformTypeIdentifiers

/**
 * 🦊 Translate with Ember — iOS Action Extension
 *
 * Appears in the share/action sheet when text is selected in any app.
 * Receives the selected text, sends it to the main app via deep link,
 * which routes to the translate screen for NLLB translation.
 *
 * The extension itself is lightweight — it just captures the text
 * and hands off to the main app where the full translation UI lives.
 */
class ActionViewController: UIViewController {

    @IBOutlet weak var statusLabel: UILabel!

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.024, green: 0.024, blue: 0.035, alpha: 1.0) // #060609

        // Extract text from the extension context
        guard let extensionItems = extensionContext?.inputItems as? [NSExtensionItem] else {
            closeExtension()
            return
        }

        for item in extensionItems {
            guard let attachments = item.attachments else { continue }
            for provider in attachments {
                if provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
                    provider.loadItem(forTypeIdentifier: UTType.plainText.identifier, options: nil) { [weak self] (text, error) in
                        guard let text = text as? String, !text.isEmpty else {
                            self?.closeExtension()
                            return
                        }
                        DispatchQueue.main.async {
                            self?.openMainApp(with: text)
                        }
                    }
                    return
                }
            }
        }

        closeExtension()
    }

    /// Opens the main Fireside app with the selected text via deep link
    private func openMainApp(with text: String) {
        guard let encoded = text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "valhalla://translate?text=\(encoded)") else {
            closeExtension()
            return
        }

        // Open the main app
        var responder: UIResponder? = self
        while responder != nil {
            if let app = responder as? UIApplication {
                app.open(url, options: [:], completionHandler: nil)
                break
            }
            responder = responder?.next
        }

        // Close extension after a brief delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in
            self?.closeExtension()
        }
    }

    /// Alternative: directly show translation in the extension view
    /// (for when the main app isn't needed)
    private func showInExtension(text: String) {
        statusLabel?.text = "Opening Fireside..."
    }

    private func closeExtension() {
        extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
    }

    @IBAction func doneButtonTapped(_ sender: Any) {
        closeExtension()
    }
}
