import UIKit
import UniformTypeIdentifiers

/**
 * 🦊 Translate with Ember — Inline iOS Action Extension
 *
 * Shows a compact overlay INSIDE the current app (WhatsApp, iMessage, etc.)
 * instead of bouncing to the full Fireside app.
 *
 * Flow: Select text → Share → "Translate with Ember" → overlay appears →
 * auto-translates → tap Copy → overlay dismisses → still in WhatsApp.
 *
 * Translation priority:
 *   1. Home PC (NLLB-200) via stored host IP → private, 200 languages
 *   2. Google Translate (cloud) → fallback, 130+ languages
 */
class ActionViewController: UIViewController {

    // ── UI Elements (built in code, no storyboard) ──
    private let containerView = UIView()
    private let titleLabel = UILabel()
    private let sourceLabel = UILabel()
    private let sourceText = UITextView()
    private let resultText = UITextView()
    private let copyButton = UIButton(type: .system)
    private let closeButton = UIButton(type: .system)
    private let statusLabel = UILabel()
    private let spinner = UIActivityIndicatorView(style: .medium)
    private let langLabel = UILabel()

    private let accentColor = UIColor(red: 232/255, green: 113/255, blue: 44/255, alpha: 1.0) // Ember orange
    private let bgColor = UIColor(red: 0.06, green: 0.06, blue: 0.09, alpha: 1.0)
    private let cardColor = UIColor(red: 0.10, green: 0.10, blue: 0.14, alpha: 1.0)

    private var originalText = ""

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor.black.withAlphaComponent(0.5)
        setupUI()
        extractText()
    }

    // ── UI Setup ──

    private func setupUI() {
        // Container (bottom sheet style)
        containerView.backgroundColor = bgColor
        containerView.layer.cornerRadius = 20
        containerView.layer.maskedCorners = [.layerMinXMinYCorner, .layerMaxXMinYCorner]
        containerView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(containerView)

        NSLayoutConstraint.activate([
            containerView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            containerView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            containerView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            containerView.heightAnchor.constraint(lessThanOrEqualTo: view.heightAnchor, multiplier: 0.6),
        ])

        // Header row: icon + title + close
        let headerStack = UIStackView()
        headerStack.axis = .horizontal
        headerStack.alignment = .center
        headerStack.translatesAutoresizingMaskIntoConstraints = false
        containerView.addSubview(headerStack)

        let iconLabel = UILabel()
        iconLabel.text = "🦊"
        iconLabel.font = .systemFont(ofSize: 24)

        titleLabel.text = "Translate with Ember"
        titleLabel.font = .boldSystemFont(ofSize: 17)
        titleLabel.textColor = .white

        closeButton.setTitle("✕", for: .normal)
        closeButton.titleLabel?.font = .systemFont(ofSize: 20)
        closeButton.tintColor = UIColor.white.withAlphaComponent(0.5)
        closeButton.addTarget(self, action: #selector(closeTapped), for: .touchUpInside)

        headerStack.addArrangedSubview(iconLabel)
        headerStack.addArrangedSubview(titleLabel)
        headerStack.addArrangedSubview(UIView()) // spacer
        headerStack.addArrangedSubview(closeButton)
        headerStack.spacing = 8

        // Source text (compact, non-editable)
        sourceLabel.text = "Source"
        sourceLabel.font = .systemFont(ofSize: 11, weight: .medium)
        sourceLabel.textColor = UIColor.white.withAlphaComponent(0.4)

        sourceText.backgroundColor = cardColor
        sourceText.textColor = UIColor.white.withAlphaComponent(0.7)
        sourceText.font = .systemFont(ofSize: 14)
        sourceText.isEditable = false
        sourceText.isScrollEnabled = true
        sourceText.layer.cornerRadius = 10
        sourceText.textContainerInset = UIEdgeInsets(top: 10, left: 10, bottom: 10, right: 10)
        sourceText.translatesAutoresizingMaskIntoConstraints = false

        // Status + spinner
        let statusStack = UIStackView()
        statusStack.axis = .horizontal
        statusStack.spacing = 8
        statusStack.alignment = .center

        spinner.color = accentColor
        spinner.startAnimating()

        statusLabel.text = "Translating..."
        statusLabel.font = .systemFont(ofSize: 13)
        statusLabel.textColor = accentColor

        statusStack.addArrangedSubview(spinner)
        statusStack.addArrangedSubview(statusLabel)

        // Result text
        resultText.backgroundColor = UIColor(red: 232/255, green: 113/255, blue: 44/255, alpha: 0.08)
        resultText.textColor = .white
        resultText.font = .systemFont(ofSize: 16)
        resultText.isEditable = false
        resultText.isScrollEnabled = true
        resultText.layer.cornerRadius = 10
        resultText.layer.borderWidth = 1
        resultText.layer.borderColor = accentColor.withAlphaComponent(0.3).cgColor
        resultText.textContainerInset = UIEdgeInsets(top: 12, left: 12, bottom: 12, right: 12)
        resultText.isHidden = true
        resultText.translatesAutoresizingMaskIntoConstraints = false

        // Language badge
        langLabel.text = ""
        langLabel.font = .systemFont(ofSize: 11, weight: .medium)
        langLabel.textColor = accentColor
        langLabel.isHidden = true

        // Copy button
        copyButton.setTitle("📋  Copy Translation", for: .normal)
        copyButton.titleLabel?.font = .boldSystemFont(ofSize: 15)
        copyButton.tintColor = bgColor
        copyButton.backgroundColor = accentColor
        copyButton.layer.cornerRadius = 12
        copyButton.isHidden = true
        copyButton.addTarget(self, action: #selector(copyTapped), for: .touchUpInside)
        copyButton.translatesAutoresizingMaskIntoConstraints = false

        // Stack it all
        let mainStack = UIStackView(arrangedSubviews: [
            headerStack, sourceLabel, sourceText, statusStack,
            langLabel, resultText, copyButton,
        ])
        mainStack.axis = .vertical
        mainStack.spacing = 10
        mainStack.translatesAutoresizingMaskIntoConstraints = false
        containerView.addSubview(mainStack)

        NSLayoutConstraint.activate([
            mainStack.topAnchor.constraint(equalTo: containerView.topAnchor, constant: 20),
            mainStack.leadingAnchor.constraint(equalTo: containerView.leadingAnchor, constant: 20),
            mainStack.trailingAnchor.constraint(equalTo: containerView.trailingAnchor, constant: -20),
            mainStack.bottomAnchor.constraint(lessThanOrEqualTo: containerView.bottomAnchor, constant: -30),
            sourceText.heightAnchor.constraint(lessThanOrEqualToConstant: 80),
            resultText.heightAnchor.constraint(greaterThanOrEqualToConstant: 60),
            copyButton.heightAnchor.constraint(equalToConstant: 48),
        ])
    }

    // ── Extract Text ──

    private func extractText() {
        guard let items = extensionContext?.inputItems as? [NSExtensionItem] else {
            showError("No text found")
            return
        }

        for item in items {
            guard let attachments = item.attachments else { continue }
            for provider in attachments {
                if provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
                    provider.loadItem(forTypeIdentifier: UTType.plainText.identifier, options: nil) { [weak self] (text, error) in
                        guard let text = text as? String, !text.isEmpty else {
                            DispatchQueue.main.async { self?.showError("No text found") }
                            return
                        }
                        DispatchQueue.main.async {
                            self?.originalText = text
                            self?.sourceText.text = text
                            self?.translateText(text)
                        }
                    }
                    return
                }
            }
        }

        showError("No text content available")
    }

    // ── Translate (PC first → Google fallback) ──

    private func translateText(_ text: String) {
        // Google Translate — fast, auto-detect, 130+ languages
        // Detect user's preferred language (device language)
        let deviceLang = Locale.preferredLanguages.first?.prefix(2).lowercased() ?? "en"
        let targetLang = deviceLang == "en" ? "es" : deviceLang // If English, translate to Spanish by default

        let encoded = text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? text
        let urlStr = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=\(targetLang)&dt=t&q=\(encoded)"

        guard let url = URL(string: urlStr) else {
            DispatchQueue.main.async { self.showError("Translation failed") }
            return
        }

        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [Any],
                  let segments = json[0] as? [[Any]] else {
                DispatchQueue.main.async { self?.showError("Translation failed — check internet") }
                return
            }

            var translated = ""
            for segment in segments {
                if let part = segment[0] as? String {
                    translated += part
                }
            }

            let detectedLang = (json.count > 2 ? json[2] as? String : nil) ?? "auto"

            DispatchQueue.main.async {
                if !translated.isEmpty {
                    self?.langLabel.text = "\(detectedLang) → \(targetLang)"
                    self?.langLabel.isHidden = false
                    self?.showResult(translated, source: "☁️ Google Translate")
                } else {
                    self?.showError("No translation available")
                }
            }
        }.resume()
    }

    // ── Show Result ──

    private func showResult(_ text: String, source: String) {
        spinner.stopAnimating()
        statusLabel.text = source
        statusLabel.textColor = source.contains("Home") ?
            UIColor(red: 34/255, green: 197/255, blue: 94/255, alpha: 1.0) : // green
            UIColor(red: 245/255, green: 158/255, blue: 11/255, alpha: 1.0)  // yellow

        resultText.text = text
        resultText.isHidden = false
        copyButton.isHidden = false
    }

    private func showError(_ message: String) {
        spinner.stopAnimating()
        statusLabel.text = message
        statusLabel.textColor = UIColor(red: 239/255, green: 68/255, blue: 68/255, alpha: 1.0)
    }

    // ── Actions ──

    @objc private func copyTapped() {
        UIPasteboard.general.string = resultText.text
        copyButton.setTitle("✅  Copied!", for: .normal)
        copyButton.backgroundColor = UIColor(red: 34/255, green: 197/255, blue: 94/255, alpha: 1.0)

        // Auto-close after brief moment
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { [weak self] in
            self?.extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
        }
    }

    @objc private func closeTapped() {
        extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
    }
}
