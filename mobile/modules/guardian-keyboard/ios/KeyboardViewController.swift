import UIKit

/**
 * 🛡️ Guardian Keyboard — Custom iOS Keyboard Extension
 *
 * A full QWERTY keyboard with two superpowers:
 *   1. Guardian — analyzes text as you type, shows a warning bar for risky messages
 *      (late night, angry, ex-partner, ALL CAPS, profanity)
 *   2. Translate — globe button translates current text via LAN NLLB-200 or Google fallback
 *
 * Design matches the Fireside brand: dark charcoal keys, fire-orange accents,
 * Guardian bar with red→orange gradient.
 *
 * Port of guardian.py heuristics to pure Swift (no external deps).
 */
class KeyboardViewController: UIInputViewController {

    // ── Brand Colors ──
    private let bgColor       = UIColor(red: 0.06, green: 0.06, blue: 0.09, alpha: 1.0)  // #0F0F17
    private let keyColor      = UIColor(red: 0.16, green: 0.16, blue: 0.23, alpha: 1.0)  // #2A2A3A
    private let keyHighlight  = UIColor(red: 0.24, green: 0.24, blue: 0.32, alpha: 1.0)  // #3D3D52
    private let textColor     = UIColor.white
    private let dimText       = UIColor(white: 1.0, alpha: 0.5)
    private let accentColor   = UIColor(red: 232/255, green: 113/255, blue: 44/255, alpha: 1.0) // #E8712C
    private let dangerColor   = UIColor(red: 255/255, green: 68/255, blue: 102/255, alpha: 1.0) // #FF4466
    private let warningStart  = UIColor(red: 232/255, green: 113/255, blue: 44/255, alpha: 1.0)
    private let warningEnd    = UIColor(red: 255/255, green: 68/255, blue: 102/255, alpha: 1.0)

    // ── State ──
    private var isShifted = false
    private var isCaps = false
    private var isNumberMode = false
    private var isSymbolMode = false
    private var guardianTimer: Timer?
    private var currentGuardianWarning: GuardianResult?

    // ── UI References ──
    private var keyboardStack: UIStackView!
    private var guardianBar: UIView!
    private var guardianLabel: UILabel!
    private var guardianEmoji: UILabel!
    private var softerButton: UIButton!
    private var ignoreButton: UIButton!
    private var letterKeys: [[UIButton]] = []
    private var spaceBar: UIButton!

    // ── Key Layouts ──
    private let letterRows = [
        ["Q","W","E","R","T","Y","U","I","O","P"],
        ["A","S","D","F","G","H","J","K","L"],
        ["Z","X","C","V","B","N","M"]
    ]
    private let numberRows = [
        ["1","2","3","4","5","6","7","8","9","0"],
        ["-","/",":",";","(",")","$","&","@","\""],
        [".",",","?","!","'"]
    ]
    private let symbolRows = [
        ["[","]","{","}","#","%","^","*","+","="],
        ["_","\\","|","~","<",">","€","£","¥","•"],
        [".",",","?","!","'"]
    ]

    // MARK: - Lifecycle

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = bgColor
        buildKeyboard()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        startGuardianMonitoring()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        guardianTimer?.invalidate()
    }

    override func textDidChange(_ textInput: UITextInput?) {
        super.textDidChange(textInput)
        // Auto-uncapitalize after typing
        if isShifted && !isCaps {
            isShifted = false
            updateKeyLabels()
        }
    }

    // MARK: - Build Keyboard

    private func buildKeyboard() {
        // Main vertical stack
        keyboardStack = UIStackView()
        keyboardStack.axis = .vertical
        keyboardStack.spacing = 0
        keyboardStack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(keyboardStack)

        NSLayoutConstraint.activate([
            keyboardStack.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            keyboardStack.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            keyboardStack.topAnchor.constraint(equalTo: view.topAnchor),
            keyboardStack.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])

        // Guardian warning bar (hidden initially)
        buildGuardianBar()

        // Key rows
        buildLetterRows()

        // Bottom toolbar
        buildToolbar()
    }

    // MARK: - Guardian Warning Bar

    private func buildGuardianBar() {
        guardianBar = UIView()
        guardianBar.isHidden = true
        guardianBar.translatesAutoresizingMaskIntoConstraints = false

        // Gradient background
        let gradient = CAGradientLayer()
        gradient.colors = [warningEnd.cgColor, warningStart.cgColor]
        gradient.startPoint = CGPoint(x: 0, y: 0.5)
        gradient.endPoint = CGPoint(x: 1, y: 0.5)
        gradient.cornerRadius = 10

        guardianBar.layer.insertSublayer(gradient, at: 0)
        guardianBar.layer.cornerRadius = 10
        guardianBar.clipsToBounds = true

        // Content stack
        let contentStack = UIStackView()
        contentStack.axis = .horizontal
        contentStack.alignment = .center
        contentStack.spacing = 8
        contentStack.translatesAutoresizingMaskIntoConstraints = false

        // Companion emoji
        guardianEmoji = UILabel()
        guardianEmoji.text = companionEmoji()
        guardianEmoji.font = .systemFont(ofSize: 28)

        // Warning text
        let textStack = UIStackView()
        textStack.axis = .vertical
        textStack.spacing = 1

        let headerLabel = UILabel()
        headerLabel.text = "\(companionEmoji()) \(companionName()) says:"
        headerLabel.font = .boldSystemFont(ofSize: 11)
        headerLabel.textColor = UIColor.white.withAlphaComponent(0.9)

        guardianLabel = UILabel()
        guardianLabel.text = ""
        guardianLabel.font = .systemFont(ofSize: 13, weight: .medium)
        guardianLabel.textColor = .white
        guardianLabel.numberOfLines = 2
        guardianLabel.lineBreakMode = .byTruncatingTail

        textStack.addArrangedSubview(headerLabel)
        textStack.addArrangedSubview(guardianLabel)

        // Buttons
        softerButton = makePillButton(title: "Softer ✨", bg: UIColor.white.withAlphaComponent(0.25))
        softerButton.addTarget(self, action: #selector(softerTapped), for: .touchUpInside)

        ignoreButton = makePillButton(title: "Ignore", bg: UIColor.white.withAlphaComponent(0.15))
        ignoreButton.addTarget(self, action: #selector(ignoreTapped), for: .touchUpInside)

        let buttonStack = UIStackView(arrangedSubviews: [softerButton, ignoreButton])
        buttonStack.axis = .horizontal
        buttonStack.spacing = 6

        contentStack.addArrangedSubview(guardianEmoji)
        contentStack.addArrangedSubview(textStack)
        contentStack.addArrangedSubview(buttonStack)

        guardianBar.addSubview(contentStack)

        // Wrap in a container with margins
        let barContainer = UIView()
        barContainer.translatesAutoresizingMaskIntoConstraints = false
        barContainer.addSubview(guardianBar)

        NSLayoutConstraint.activate([
            guardianBar.leadingAnchor.constraint(equalTo: barContainer.leadingAnchor, constant: 6),
            guardianBar.trailingAnchor.constraint(equalTo: barContainer.trailingAnchor, constant: -6),
            guardianBar.topAnchor.constraint(equalTo: barContainer.topAnchor, constant: 4),
            guardianBar.bottomAnchor.constraint(equalTo: barContainer.bottomAnchor, constant: -4),
            guardianBar.heightAnchor.constraint(greaterThanOrEqualToConstant: 52),

            contentStack.leadingAnchor.constraint(equalTo: guardianBar.leadingAnchor, constant: 10),
            contentStack.trailingAnchor.constraint(equalTo: guardianBar.trailingAnchor, constant: -10),
            contentStack.topAnchor.constraint(equalTo: guardianBar.topAnchor, constant: 8),
            contentStack.bottomAnchor.constraint(equalTo: guardianBar.bottomAnchor, constant: -8),
        ])

        keyboardStack.addArrangedSubview(barContainer)

        // Update gradient frame on layout
        barContainer.layoutIfNeeded()
        gradient.frame = guardianBar.bounds
        guardianBar.tag = 999 // tag for finding gradient layer later
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        // Update gradient frame
        if let gradientLayer = guardianBar.layer.sublayers?.first as? CAGradientLayer {
            gradientLayer.frame = guardianBar.bounds
        }
    }

    private func makePillButton(title: String, bg: UIColor) -> UIButton {
        let btn = UIButton(type: .system)
        btn.setTitle(title, for: .normal)
        btn.titleLabel?.font = .systemFont(ofSize: 11, weight: .semibold)
        btn.setTitleColor(.white, for: .normal)
        btn.backgroundColor = bg
        btn.layer.cornerRadius = 12
        btn.contentEdgeInsets = UIEdgeInsets(top: 5, left: 12, bottom: 5, right: 12)
        return btn
    }

    // MARK: - Letter Rows

    private func buildLetterRows() {
        letterKeys = []

        for (rowIndex, row) in letterRows.enumerated() {
            let rowStack = UIStackView()
            rowStack.axis = .horizontal
            rowStack.distribution = .fillEqually
            rowStack.spacing = 4
            rowStack.translatesAutoresizingMaskIntoConstraints = false

            // Row container with side padding
            let rowContainer = UIView()
            rowContainer.translatesAutoresizingMaskIntoConstraints = false

            var rowButtons: [UIButton] = []

            // Shift key on row 2 (left side)
            if rowIndex == 2 {
                let shiftBtn = makeSpecialKey(icon: "⬆", width: 42)
                shiftBtn.addTarget(self, action: #selector(shiftTapped), for: .touchUpInside)
                let doubleTap = UITapGestureRecognizer(target: self, action: #selector(capsLockTapped))
                doubleTap.numberOfTapsRequired = 2
                shiftBtn.addGestureRecognizer(doubleTap)
                rowContainer.addSubview(shiftBtn)

                NSLayoutConstraint.activate([
                    shiftBtn.leadingAnchor.constraint(equalTo: rowContainer.leadingAnchor, constant: 4),
                    shiftBtn.centerYAnchor.constraint(equalTo: rowContainer.centerYAnchor),
                    shiftBtn.widthAnchor.constraint(equalToConstant: 42),
                    shiftBtn.heightAnchor.constraint(equalToConstant: 42),
                ])
            }

            for letter in row {
                let btn = makeKeyButton(title: letter)
                btn.addTarget(self, action: #selector(letterTapped(_:)), for: .touchUpInside)
                rowStack.addArrangedSubview(btn)
                rowButtons.append(btn)
            }

            rowContainer.addSubview(rowStack)

            let leftPad: CGFloat = rowIndex == 2 ? 50 : (rowIndex == 1 ? 16 : 4)
            let rightPad: CGFloat = rowIndex == 2 ? 50 : (rowIndex == 1 ? 16 : 4)

            NSLayoutConstraint.activate([
                rowStack.leadingAnchor.constraint(equalTo: rowContainer.leadingAnchor, constant: leftPad),
                rowStack.trailingAnchor.constraint(equalTo: rowContainer.trailingAnchor, constant: -rightPad),
                rowStack.topAnchor.constraint(equalTo: rowContainer.topAnchor, constant: 3),
                rowStack.bottomAnchor.constraint(equalTo: rowContainer.bottomAnchor, constant: -3),
                rowStack.heightAnchor.constraint(equalToConstant: 42),
            ])

            // Backspace on row 2 (right side)
            if rowIndex == 2 {
                let backBtn = makeSpecialKey(icon: "⌫", width: 42)
                backBtn.addTarget(self, action: #selector(backspaceTapped), for: .touchUpInside)
                let longPress = UILongPressGestureRecognizer(target: self, action: #selector(backspaceLongPress(_:)))
                backBtn.addGestureRecognizer(longPress)
                rowContainer.addSubview(backBtn)

                NSLayoutConstraint.activate([
                    backBtn.trailingAnchor.constraint(equalTo: rowContainer.trailingAnchor, constant: -4),
                    backBtn.centerYAnchor.constraint(equalTo: rowContainer.centerYAnchor),
                    backBtn.widthAnchor.constraint(equalToConstant: 42),
                    backBtn.heightAnchor.constraint(equalToConstant: 42),
                ])
            }

            keyboardStack.addArrangedSubview(rowContainer)
            letterKeys.append(rowButtons)
        }
    }

    private func makeKeyButton(title: String) -> UIButton {
        let btn = UIButton(type: .system)
        btn.setTitle(title, for: .normal)
        btn.titleLabel?.font = .systemFont(ofSize: 22, weight: .regular)
        btn.setTitleColor(textColor, for: .normal)
        btn.backgroundColor = keyColor
        btn.layer.cornerRadius = 6
        btn.layer.shadowColor = UIColor.black.cgColor
        btn.layer.shadowOffset = CGSize(width: 0, height: 1)
        btn.layer.shadowOpacity = 0.4
        btn.layer.shadowRadius = 1
        return btn
    }

    private func makeSpecialKey(icon: String, width: CGFloat) -> UIButton {
        let btn = UIButton(type: .system)
        btn.setTitle(icon, for: .normal)
        btn.titleLabel?.font = .systemFont(ofSize: 18)
        btn.setTitleColor(textColor, for: .normal)
        btn.backgroundColor = UIColor(white: 0.2, alpha: 1.0)
        btn.layer.cornerRadius = 6
        btn.translatesAutoresizingMaskIntoConstraints = false
        return btn
    }

    // MARK: - Bottom Toolbar

    private func buildToolbar() {
        let toolbar = UIStackView()
        toolbar.axis = .horizontal
        toolbar.spacing = 6
        toolbar.alignment = .center
        toolbar.distribution = .fill
        toolbar.translatesAutoresizingMaskIntoConstraints = false

        let toolbarContainer = UIView()
        toolbarContainer.translatesAutoresizingMaskIntoConstraints = false

        // Globe / Translate button
        let translateBtn = UIButton(type: .system)
        translateBtn.setTitle("🌐", for: .normal)
        translateBtn.titleLabel?.font = .systemFont(ofSize: 22)
        translateBtn.addTarget(self, action: #selector(translateTapped), for: .touchUpInside)
        translateBtn.translatesAutoresizingMaskIntoConstraints = false
        translateBtn.widthAnchor.constraint(equalToConstant: 40).isActive = true

        // 123 / ABC toggle
        let modeBtn = UIButton(type: .system)
        modeBtn.setTitle("123", for: .normal)
        modeBtn.titleLabel?.font = .systemFont(ofSize: 15, weight: .medium)
        modeBtn.setTitleColor(textColor, for: .normal)
        modeBtn.backgroundColor = UIColor(white: 0.2, alpha: 1.0)
        modeBtn.layer.cornerRadius = 6
        modeBtn.addTarget(self, action: #selector(modeTapped), for: .touchUpInside)
        modeBtn.translatesAutoresizingMaskIntoConstraints = false
        modeBtn.widthAnchor.constraint(equalToConstant: 50).isActive = true
        modeBtn.heightAnchor.constraint(equalToConstant: 42).isActive = true
        modeBtn.tag = 100 // tag to update label

        // Space bar
        spaceBar = UIButton(type: .system)
        spaceBar.setTitle("space", for: .normal)
        spaceBar.titleLabel?.font = .systemFont(ofSize: 14, weight: .regular)
        spaceBar.setTitleColor(dimText, for: .normal)
        spaceBar.backgroundColor = keyColor
        spaceBar.layer.cornerRadius = 6
        spaceBar.addTarget(self, action: #selector(spaceTapped), for: .touchUpInside)
        spaceBar.translatesAutoresizingMaskIntoConstraints = false
        spaceBar.heightAnchor.constraint(equalToConstant: 42).isActive = true

        // Subtitle under space
        let subtitle = UILabel()
        subtitle.text = "Guardian Keyboard"
        subtitle.font = .systemFont(ofSize: 9, weight: .medium)
        subtitle.textColor = UIColor(white: 1.0, alpha: 0.25)
        subtitle.textAlignment = .center
        subtitle.translatesAutoresizingMaskIntoConstraints = false
        spaceBar.addSubview(subtitle)
        NSLayoutConstraint.activate([
            subtitle.centerXAnchor.constraint(equalTo: spaceBar.centerXAnchor),
            subtitle.bottomAnchor.constraint(equalTo: spaceBar.bottomAnchor, constant: -3),
        ])

        // Return button
        let returnBtn = UIButton(type: .system)
        returnBtn.setTitle("return", for: .normal)
        returnBtn.titleLabel?.font = .systemFont(ofSize: 15, weight: .medium)
        returnBtn.setTitleColor(textColor, for: .normal)
        returnBtn.backgroundColor = UIColor(white: 0.2, alpha: 1.0)
        returnBtn.layer.cornerRadius = 6
        returnBtn.addTarget(self, action: #selector(returnTapped), for: .touchUpInside)
        returnBtn.translatesAutoresizingMaskIntoConstraints = false
        returnBtn.widthAnchor.constraint(equalToConstant: 72).isActive = true
        returnBtn.heightAnchor.constraint(equalToConstant: 42).isActive = true

        toolbar.addArrangedSubview(translateBtn)
        toolbar.addArrangedSubview(modeBtn)
        toolbar.addArrangedSubview(spaceBar)
        toolbar.addArrangedSubview(returnBtn)

        toolbarContainer.addSubview(toolbar)

        NSLayoutConstraint.activate([
            toolbar.leadingAnchor.constraint(equalTo: toolbarContainer.leadingAnchor, constant: 4),
            toolbar.trailingAnchor.constraint(equalTo: toolbarContainer.trailingAnchor, constant: -4),
            toolbar.topAnchor.constraint(equalTo: toolbarContainer.topAnchor, constant: 3),
            toolbar.bottomAnchor.constraint(equalTo: toolbarContainer.bottomAnchor, constant: -6),
        ])

        keyboardStack.addArrangedSubview(toolbarContainer)
    }

    // MARK: - Key Actions

    @objc private func letterTapped(_ sender: UIButton) {
        guard var letter = sender.title(for: .normal) else { return }
        if !isShifted && !isCaps {
            letter = letter.lowercased()
        }
        textDocumentProxy.insertText(letter)

        // Haptic feedback
        let impact = UIImpactFeedbackGenerator(style: .light)
        impact.impactOccurred()

        // Key highlight animation
        UIView.animate(withDuration: 0.05, animations: {
            sender.backgroundColor = self.keyHighlight
        }) { _ in
            UIView.animate(withDuration: 0.1) {
                sender.backgroundColor = self.keyColor
            }
        }
    }

    @objc private func spaceTapped() {
        textDocumentProxy.insertText(" ")
    }

    @objc private func returnTapped() {
        textDocumentProxy.insertText("\n")
    }

    @objc private func backspaceTapped() {
        textDocumentProxy.deleteBackward()
    }

    @objc private func backspaceLongPress(_ gesture: UILongPressGestureRecognizer) {
        if gesture.state == .began {
            // Delete multiple characters on long press
            for _ in 0..<10 {
                textDocumentProxy.deleteBackward()
            }
        }
    }

    @objc private func shiftTapped() {
        isShifted.toggle()
        isCaps = false
        updateKeyLabels()
    }

    @objc private func capsLockTapped() {
        isCaps = true
        isShifted = true
        updateKeyLabels()
    }

    @objc private func modeTapped() {
        isNumberMode.toggle()
        isSymbolMode = false
        rebuildKeys()
    }

    @objc private func translateTapped() {
        translateCurrentText()
    }

    private func updateKeyLabels() {
        let rows = isNumberMode ? (isSymbolMode ? symbolRows : numberRows) : letterRows
        for (rowIdx, row) in rows.enumerated() {
            guard rowIdx < letterKeys.count else { continue }
            for (keyIdx, key) in row.enumerated() {
                guard keyIdx < letterKeys[rowIdx].count else { continue }
                let label = (isShifted || isCaps) ? key.uppercased() : key.lowercased()
                letterKeys[rowIdx][keyIdx].setTitle(label, for: .normal)
            }
        }
    }

    private func rebuildKeys() {
        // Remove existing key rows (keep guardian bar at index 0 and toolbar at end)
        let subviews = keyboardStack.arrangedSubviews
        // Remove key row containers (indices 1..<count-1)
        for i in stride(from: subviews.count - 2, through: 1, by: -1) {
            let view = subviews[i]
            keyboardStack.removeArrangedSubview(view)
            view.removeFromSuperview()
        }

        letterKeys = []
        let rows = isNumberMode ? (isSymbolMode ? symbolRows : numberRows) : letterRows

        for (rowIndex, row) in rows.enumerated() {
            let rowStack = UIStackView()
            rowStack.axis = .horizontal
            rowStack.distribution = .fillEqually
            rowStack.spacing = 4
            rowStack.translatesAutoresizingMaskIntoConstraints = false

            let rowContainer = UIView()
            rowContainer.translatesAutoresizingMaskIntoConstraints = false

            var rowButtons: [UIButton] = []

            // Shift / Symbol toggle on row 2
            if rowIndex == 2 && !isNumberMode {
                let shiftBtn = makeSpecialKey(icon: "⬆", width: 42)
                shiftBtn.addTarget(self, action: #selector(shiftTapped), for: .touchUpInside)
                rowContainer.addSubview(shiftBtn)
                NSLayoutConstraint.activate([
                    shiftBtn.leadingAnchor.constraint(equalTo: rowContainer.leadingAnchor, constant: 4),
                    shiftBtn.centerYAnchor.constraint(equalTo: rowContainer.centerYAnchor),
                    shiftBtn.widthAnchor.constraint(equalToConstant: 42),
                    shiftBtn.heightAnchor.constraint(equalToConstant: 42),
                ])
            } else if rowIndex == 2 && isNumberMode {
                let symBtn = makeSpecialKey(icon: isSymbolMode ? "123" : "#+=", width: 42)
                symBtn.titleLabel?.font = .systemFont(ofSize: 13, weight: .medium)
                symBtn.addTarget(self, action: #selector(symbolToggleTapped), for: .touchUpInside)
                rowContainer.addSubview(symBtn)
                NSLayoutConstraint.activate([
                    symBtn.leadingAnchor.constraint(equalTo: rowContainer.leadingAnchor, constant: 4),
                    symBtn.centerYAnchor.constraint(equalTo: rowContainer.centerYAnchor),
                    symBtn.widthAnchor.constraint(equalToConstant: 42),
                    symBtn.heightAnchor.constraint(equalToConstant: 42),
                ])
            }

            for letter in row {
                let btn = makeKeyButton(title: letter)
                btn.addTarget(self, action: #selector(letterTapped(_:)), for: .touchUpInside)
                rowStack.addArrangedSubview(btn)
                rowButtons.append(btn)
            }

            rowContainer.addSubview(rowStack)
            let leftPad: CGFloat = rowIndex == 2 ? 50 : (rowIndex == 1 && !isNumberMode ? 16 : 4)
            let rightPad: CGFloat = rowIndex == 2 ? 50 : (rowIndex == 1 && !isNumberMode ? 16 : 4)

            NSLayoutConstraint.activate([
                rowStack.leadingAnchor.constraint(equalTo: rowContainer.leadingAnchor, constant: leftPad),
                rowStack.trailingAnchor.constraint(equalTo: rowContainer.trailingAnchor, constant: -rightPad),
                rowStack.topAnchor.constraint(equalTo: rowContainer.topAnchor, constant: 3),
                rowStack.bottomAnchor.constraint(equalTo: rowContainer.bottomAnchor, constant: -3),
                rowStack.heightAnchor.constraint(equalToConstant: 42),
            ])

            // Backspace on row 2
            if rowIndex == 2 {
                let backBtn = makeSpecialKey(icon: "⌫", width: 42)
                backBtn.addTarget(self, action: #selector(backspaceTapped), for: .touchUpInside)
                rowContainer.addSubview(backBtn)
                NSLayoutConstraint.activate([
                    backBtn.trailingAnchor.constraint(equalTo: rowContainer.trailingAnchor, constant: -4),
                    backBtn.centerYAnchor.constraint(equalTo: rowContainer.centerYAnchor),
                    backBtn.widthAnchor.constraint(equalToConstant: 42),
                    backBtn.heightAnchor.constraint(equalToConstant: 42),
                ])
            }

            // Insert before toolbar (last element)
            let insertIndex = keyboardStack.arrangedSubviews.count - 1
            keyboardStack.insertArrangedSubview(rowContainer, at: insertIndex)
            letterKeys.append(rowButtons)
        }

        // Update mode button label
        if let modeBtn = view.viewWithTag(100) as? UIButton {
            modeBtn.setTitle(isNumberMode ? "ABC" : "123", for: .normal)
        }
    }

    @objc private func symbolToggleTapped() {
        isSymbolMode.toggle()
        rebuildKeys()
    }

    // MARK: - Guardian Engine (Swift port of guardian.py)

    struct GuardianResult {
        let riskLevel: String      // "none", "low", "medium", "high"
        let warning: String
        let softerVersion: String
        let flags: [GuardianFlag]
    }

    struct GuardianFlag {
        let type: String
        let severity: String
        let reason: String
    }

    private func analyzeMessage(_ text: String) -> GuardianResult {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return GuardianResult(riskLevel: "none", warning: "", softerVersion: "", flags: [])
        }

        let lower = text.lowercased()
        var flags: [GuardianFlag] = []

        // 1. Late night check (midnight–5am)
        let hour = Calendar.current.component(.hour, from: Date())
        if hour >= 0 && hour <= 5 {
            flags.append(GuardianFlag(
                type: "late_night",
                severity: "medium",
                reason: "It's late. Messages sent between midnight and 5am have a higher regret rate."
            ))
        }

        // 2. ALL CAPS detection
        let alphaChars = text.filter { $0.isLetter }
        if !alphaChars.isEmpty {
            let capsRatio = Double(alphaChars.filter { $0.isUppercase }.count) / Double(alphaChars.count)
            if capsRatio > 0.7 && text.count > 10 {
                flags.append(GuardianFlag(
                    type: "all_caps",
                    severity: "medium",
                    reason: "ALL CAPS can come across as shouting."
                ))
            }
        }

        // 3. Ex-partner detection
        let exPatterns = ["\\bex\\b", "\\bex-", "ex girlfriend", "ex boyfriend",
                          "ex wife", "ex husband", "my ex", "old flame", "former partner"]
        for pattern in exPatterns {
            if lower.range(of: pattern, options: .regularExpression) != nil {
                flags.append(GuardianFlag(
                    type: "ex_partner",
                    severity: "high",
                    reason: "This might be going to an ex. Sleep on it?"
                ))
                break
            }
        }

        // 4. Reply-all detection
        let replyAllPatterns = ["reply.?all", "@everyone", "@all", "@channel", "@here",
                                "all hands", "entire team"]
        for pattern in replyAllPatterns {
            if lower.range(of: pattern, options: .regularExpression) != nil {
                flags.append(GuardianFlag(
                    type: "reply_all",
                    severity: "high",
                    reason: "This looks like a reply-all or broadcast. Everyone gets this."
                ))
                break
            }
        }

        // 5. Profanity density
        let profanity = ["fuck", "shit", "damn", "hell", "ass", "bitch", "bastard", "crap"]
        let wordCount = max(text.split(separator: " ").count, 1)
        let profanityCount = profanity.filter { lower.contains($0) }.count
        if profanityCount >= 2 || (Double(profanityCount) / Double(wordCount) > 0.1) {
            flags.append(GuardianFlag(
                type: "profanity",
                severity: "medium",
                reason: "High profanity density. Might want to cool down first."
            ))
        }

        // 6. Exclamation density
        if text.filter({ $0 == "!" }).count >= 3 {
            flags.append(GuardianFlag(
                type: "exclamation_heavy",
                severity: "low",
                reason: "Lots of exclamation marks. High energy detected."
            ))
        }

        // 7. Angry sentiment + long message
        let sentiment = classifySentiment(text)
        if text.count > 500 && sentiment == "angry" {
            flags.append(GuardianFlag(
                type: "angry_wall",
                severity: "high",
                reason: "Long angry message. These rarely land well."
            ))
        }

        // Calculate risk level
        let severityScores: [String: Int] = ["low": 1, "medium": 2, "high": 3]
        let totalRisk = flags.reduce(0) { $0 + (severityScores[$1.severity] ?? 0) }

        let riskLevel: String
        if totalRisk >= 5 { riskLevel = "high" }
        else if totalRisk >= 2 { riskLevel = "medium" }
        else if totalRisk >= 1 { riskLevel = "low" }
        else { riskLevel = "none" }

        // Species-specific warning
        let warning = companionWarning(for: riskLevel)
        let softer = riskLevel != "none" ? suggestSofter(text) : ""

        return GuardianResult(riskLevel: riskLevel, warning: warning, softerVersion: softer, flags: flags)
    }

    private func classifySentiment(_ text: String) -> String {
        let lower = text.lowercased()

        let angryWords = ["fuck", "shit", "damn", "hell", "hate", "stupid", "idiot", "moron",
                          "furious", "pissed", "angry", "rage", "screw", "bastard",
                          "wtf", "stfu", "terrible", "worst", "disgusting", "pathetic"]
        let sadWords = ["sorry", "sad", "miss", "lonely", "hurt", "crying", "depressed",
                        "wish", "regret", "heartbroken", "lost", "empty", "alone"]
        let happyWords = ["love", "amazing", "wonderful", "great", "happy", "excited",
                          "awesome", "beautiful", "perfect", "best", "brilliant", "fantastic"]

        let angryScore = angryWords.filter { lower.contains($0) }.count
        let sadScore = sadWords.filter { lower.contains($0) }.count
        let happyScore = happyWords.filter { lower.contains($0) }.count

        let maxScore = max(angryScore, sadScore, happyScore)
        if maxScore == 0 { return "neutral" }
        if angryScore == maxScore { return "angry" }
        if sadScore == maxScore { return "sad" }
        return "happy"
    }

    private func suggestSofter(_ text: String) -> String {
        var result = text
        let replacements: [(String, String)] = [
            ("\\byou always\\b", "it sometimes feels like"),
            ("\\byou never\\b", "I wish"),
            ("\\byou're wrong\\b", "I see it differently"),
            ("\\bthat's stupid\\b", "I'm not sure about that approach"),
            ("\\bI hate\\b", "I'm frustrated with"),
            ("\\bshut up\\b", "let me finish"),
            ("\\bwhatever\\b", "I need a moment"),
            ("\\bI don't care\\b", "I need to think about this"),
            ("\\bleave me alone\\b", "I need some space right now"),
        ]

        for (pattern, replacement) in replacements {
            if let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) {
                result = regex.stringByReplacingMatches(
                    in: result,
                    range: NSRange(result.startIndex..., in: result),
                    withTemplate: replacement
                )
            }
        }
        return result != text ? result : ""
    }

    // MARK: - Companion Personality

    private func companionEmoji() -> String {
        let species = loadCompanionSpecies()
        switch species {
        case "dog": return "🐕"
        case "penguin": return "🐧"
        case "fox": return "🦊"
        case "owl": return "🦉"
        case "dragon": return "🐉"
        default: return "🐱"
        }
    }

    private func companionName() -> String {
        let defaults = UserDefaults(suiteName: "group.com.valhalla.companion")
        return defaults?.string(forKey: "companion_name") ?? "Sir Wadsworth"
    }

    private func loadCompanionSpecies() -> String {
        let defaults = UserDefaults(suiteName: "group.com.valhalla.companion")
        return defaults?.string(forKey: "companion_species") ?? "penguin"
    }

    private func companionWarning(for riskLevel: String) -> String {
        let species = loadCompanionSpecies()
        let warnings: [String: [String: String]] = [
            "cat": [
                "high": "Are you sure? This sounds like 2am energy.",
                "medium": "Hmm. I'd sleep on this one.",
                "low": "Just checking — you good?",
            ],
            "dog": [
                "high": "Hey buddy... are we sure about this one? 🥺",
                "medium": "Want to take a walk first? Clear your head?",
                "low": "I believe in you! But maybe re-read it?",
            ],
            "penguin": [
                "high": "Sir. I must advise against this correspondence.",
                "medium": "Perhaps a more... measured approach?",
                "low": "Noted. Proceed with mild caution.",
            ],
            "fox": [
                "high": "My instincts say wait. Trust the instincts.",
                "medium": "There's a smarter play here. Want to think on it?",
                "low": "Looks fine, but I'm watching.",
            ],
            "owl": [
                "high": "Historically, messages like this have a 78% regret rate.",
                "medium": "The data suggests a 15-minute cooling period.",
                "low": "Minor risk detected. Proceeding is acceptable.",
            ],
            "dragon": [
                "high": "I RESPECT THE ENERGY but your boss might not.",
                "medium": "Save the fire for something worth burning.",
                "low": "This is fine. Probably. SEND IT.",
            ],
        ]

        let speciesWarnings = warnings[species] ?? warnings["cat"]!
        return speciesWarnings[riskLevel] ?? ""
    }

    // MARK: - Guardian Monitoring

    private func startGuardianMonitoring() {
        guardianTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            self?.runGuardianAnalysis()
        }
    }

    private func runGuardianAnalysis() {
        // Read current text from the text field
        guard let proxy = textDocumentProxy as? UITextDocumentProxy else { return }
        let beforeCursor = proxy.documentContextBeforeInput ?? ""
        let afterCursor = proxy.documentContextAfterInput ?? ""
        let fullText = beforeCursor + afterCursor

        guard fullText.count > 5 else {
            hideGuardianBar()
            return
        }

        let result = analyzeMessage(fullText)

        if result.riskLevel != "none" {
            currentGuardianWarning = result
            showGuardianBar(result)
        } else {
            currentGuardianWarning = nil
            hideGuardianBar()
        }
    }

    private func showGuardianBar(_ result: GuardianResult) {
        guardianLabel.text = result.warning
        softerButton.isHidden = result.softerVersion.isEmpty

        if guardianBar.isHidden {
            guardianBar.isHidden = false
            guardianBar.alpha = 0
            UIView.animate(withDuration: 0.25) {
                self.guardianBar.alpha = 1
            }
        }
    }

    private func hideGuardianBar() {
        if !guardianBar.isHidden {
            UIView.animate(withDuration: 0.2, animations: {
                self.guardianBar.alpha = 0
            }) { _ in
                self.guardianBar.isHidden = true
            }
        }
    }

    @objc private func softerTapped() {
        guard let result = currentGuardianWarning, !result.softerVersion.isEmpty else { return }

        // Replace current text with softer version
        let proxy = textDocumentProxy
        let beforeCursor = proxy.documentContextBeforeInput ?? ""
        let afterCursor = proxy.documentContextAfterInput ?? ""

        // Delete all text
        for _ in 0..<afterCursor.count {
            proxy.adjustTextPosition(byCharacterOffset: 1)
        }
        let totalLength = beforeCursor.count + afterCursor.count
        for _ in 0..<totalLength {
            proxy.deleteBackward()
        }

        // Insert softer version
        proxy.insertText(result.softerVersion)
        hideGuardianBar()

        // Haptic
        let impact = UIImpactFeedbackGenerator(style: .medium)
        impact.impactOccurred()
    }

    @objc private func ignoreTapped() {
        hideGuardianBar()
        currentGuardianWarning = nil

        // Haptic
        let selection = UISelectionFeedbackGenerator()
        selection.selectionChanged()
    }

    // MARK: - Translate Engine

    private func translateCurrentText() {
        let proxy = textDocumentProxy
        let beforeCursor = proxy.documentContextBeforeInput ?? ""
        let afterCursor = proxy.documentContextAfterInput ?? ""
        let fullText = (beforeCursor + afterCursor).trimmingCharacters(in: .whitespacesAndNewlines)

        guard !fullText.isEmpty else { return }

        // Show translating state on space bar
        spaceBar.setTitle("Translating...", for: .normal)
        spaceBar.setTitleColor(accentColor, for: .normal)

        // Try LAN PC first, then Google fallback
        let pcHost = loadPCHost()
        if !pcHost.isEmpty {
            translateViaPC(fullText, host: pcHost) { [weak self] result in
                if let result = result {
                    self?.applyTranslation(result, source: "🏠 Home PC")
                } else {
                    self?.translateViaGoogle(fullText)
                }
            }
        } else {
            translateViaGoogle(fullText)
        }
    }

    private func loadPCHost() -> String {
        let defaults = UserDefaults(suiteName: "group.com.valhalla.companion")
        return defaults?.string(forKey: "pc_host") ?? ""
    }

    private func translateViaPC(_ text: String, host: String, completion: @escaping (String?) -> Void) {
        guard let url = URL(string: "http://\(host):8000/translate") else {
            completion(nil)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 5

        let deviceLang = Locale.preferredLanguages.first?.prefix(2).lowercased() ?? "en"
        let targetLang = deviceLang == "en" ? "spa_Latn" : "\(deviceLang)_Latn"

        let body: [String: Any] = ["text": text, "target_lang": targetLang]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let translated = json["translated"] as? String else {
                DispatchQueue.main.async { completion(nil) }
                return
            }
            DispatchQueue.main.async { completion(translated) }
        }.resume()
    }

    private func translateViaGoogle(_ text: String) {
        let deviceLang = Locale.preferredLanguages.first?.prefix(2).lowercased() ?? "en"
        let targetLang = deviceLang == "en" ? "es" : deviceLang

        let encoded = text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? text
        let urlStr = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=\(targetLang)&dt=t&q=\(encoded)"

        guard let url = URL(string: urlStr) else {
            resetSpaceBar()
            return
        }

        URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [Any],
                  let segments = json[0] as? [[Any]] else {
                DispatchQueue.main.async { self?.resetSpaceBar() }
                return
            }

            var translated = ""
            for segment in segments {
                if let part = segment[0] as? String {
                    translated += part
                }
            }

            DispatchQueue.main.async {
                if !translated.isEmpty {
                    self?.applyTranslation(translated, source: "☁️ Google")
                } else {
                    self?.resetSpaceBar()
                }
            }
        }.resume()
    }

    private func applyTranslation(_ translated: String, source: String) {
        let proxy = textDocumentProxy
        let beforeCursor = proxy.documentContextBeforeInput ?? ""
        let afterCursor = proxy.documentContextAfterInput ?? ""

        // Delete all text
        for _ in 0..<afterCursor.count {
            proxy.adjustTextPosition(byCharacterOffset: 1)
        }
        let totalLength = beforeCursor.count + afterCursor.count
        for _ in 0..<totalLength {
            proxy.deleteBackward()
        }

        // Insert translated text
        proxy.insertText(translated)

        // Show source on space bar briefly
        spaceBar.setTitle(source, for: .normal)
        spaceBar.setTitleColor(source.contains("Home") ?
            UIColor(red: 34/255, green: 197/255, blue: 94/255, alpha: 1.0) :
            UIColor(red: 245/255, green: 158/255, blue: 11/255, alpha: 1.0),
            for: .normal)

        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
            self?.resetSpaceBar()
        }

        // Haptic
        let impact = UIImpactFeedbackGenerator(style: .medium)
        impact.impactOccurred()
    }

    private func resetSpaceBar() {
        spaceBar.setTitle("space", for: .normal)
        spaceBar.setTitleColor(dimText, for: .normal)
    }
}
