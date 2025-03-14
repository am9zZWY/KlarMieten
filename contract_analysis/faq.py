FAQ = [
    {
        "question": "Was bietet \"Darf Vermieter Das?\"?",
        "answer": "Unser Service zeigt Ihnen einen ersten Überblick über die häufigsten Regelungen im Mietrecht. Die Informationen helfen Ihnen, Ihren Mietvertrag besser zu verstehen – aber sie ersetzen keine rechtliche Beratung. Bei konkreten Fragen sollten Sie immer eine Fachanwaltin oder eine Fachanwalt hinzuziehen.",
        "for": ["landing", "faq"]
    },
    {
        "question": "Sind die Analysen rechtlich verbindlich?",
        "answer": "Nein, die Analysen sind nicht rechtsverbindlich. Unsere Ergebnisse bieten Ihnen einen ersten Überblick und helfen, Ihren Vertrag besser zu verstehen. Sie ersetzen jedoch keine individuelle Rechtsberatung durch einen Fachanwalt. Bei konkreten rechtlichen Fragen sollten Sie immer eine Fachanwaltin oder eine Fachanwalt hinzuziehen.",
        "for": ["landing", "faq"]
    },
    {
        "question": "Wie wird die Analyse erstellt?",
        "answer": "Wir nutzen die Technologie von Mistral AI und Google Gemini. Wir übernehmen keine Garantie für die Vollständigkeit oder Richtigkeit der Ergebnisse.",
        "for": ["faq"]
    },
    {
        "question": "Kann ich mich allein auf die Analyse verlassen?",
        "answer": "Bitte verlassen Sie sich nicht nur auf die Analyse. Nutzen Sie diese nur als ersten Hinweis und holen Sie im Zweifelsfall rechtlichen Rat bei einer Fachanwaltin oder einem Fachanwalt ein.",
        "for": ["faq"]
    },
    {
        "question": "Wie gehen Sie mit meinen Daten um?",
        "answer": "Der Schutz und die Sicherheit Ihrer Daten sind uns wichtig. Ihre hochgeladenen Dokumente werden ausschließlich zur Analyse verwendet und anschließend gelöscht. Wir empfehlen dennoch, sensible Informationen vor dem Upload selbst zu entfernen.",
        "for": ["faq"]
    },
    {
        "question": "Was mache ich, wenn ich unsicher bin?",
        "answer": "Unsere Analyse soll Ihnen als hilfreiche Orientierung dienen. Bei konkreten Fragen oder Unsicherheiten raten wir dazu, einen qualifizierten Rechtsberater zu konsultieren.",
        "for": ["faq"]
    },
    {
        "question": "Warum bieten Sie diesen Service an?",
        "answer": "Wir haben diesen Service entwickelt, um Mietern zu helfen, ihre Rechte besser zu verstehen und sich gegen ungerechtfertigte Klauseln zu wehren – aus eigener Erfahrung und ohne kommerzielle Absichten.",
        "for": ["faq"]
    },
    {
        "question": "Bietet diese Seite individuelle Rechtsberatung an?",
        "answer": "Unsere Inhalte dienen ausschließlich zur allgemeinen Information und Orientierung. Wir beantworten keine individuellen Rechtsfragen per E-Mail oder anderweitig. Bei konkreten Problemen empfehlen wir, eine qualifizierte Rechtsberatung in Anspruch zu nehmen.",
        "for": ["landing", "faq"]
    },
    {
        "question": "Werden meine persönlichen Daten zensiert?",
        "answer": "Sie können in Ihrem Vertrag sensible Daten selbst schwärzen oder entfernen, bevor Sie ihn hochladen. Wir können nicht unterscheiden, welche Informationen persönlich sind. Falls dies nicht oder fehlerhaft erfolgt, können auch personenbezogene Daten verarbeitet werden – dafür übernehmen wir keine Haftung.",
        "for": ["landing", "faq"]
    },
]

FAQ_landing = [q for q in FAQ if "landing" in q["for"]]
FAQ_all = [q for q in FAQ if "faq" in q["for"]]
