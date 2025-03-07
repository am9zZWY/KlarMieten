# models.py

from django.db import models


class RentIndex(models.Model):
    wohnflaeche_qm = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Wohnfläche (qm)"
    )
    baujahr = models.IntegerField(verbose_name="Baujahr")
    zone = models.CharField(max_length=50, verbose_name="Zone")
    laermbelastung = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Lärmbelastung"
    )
    heizungsart = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Heizungsart"
    )
    bodenbelag = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Bodenbelag"
    )
    sanitaerausstattung = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Sanitärausstattung"
    )

    souterrain = models.BooleanField(
        default=False, verbose_name="Wohnung im Souterrain"
    )
    einfacher_kuechenboden = models.BooleanField(
        default=False, verbose_name="Einfacher Küchenboden"
    )
    aufzug = models.BooleanField(default=False, verbose_name="Aufzug")
    zusatzlicher_sanitarraum = models.BooleanField(
        default=False, verbose_name="Zusätzlicher Sanitärraum"
    )
    maisonette = models.BooleanField(default=False, verbose_name="Maisonette")
    einfamilienhaus = models.BooleanField(default=False, verbose_name="Einfamilienhaus")

    sanitaerausstattung_erneuert = models.BooleanField(
        default=False, verbose_name="Sanitärausstattung erneuert"
    )
    bodenbelaege_erneuert = models.BooleanField(
        default=False, verbose_name="Bodenbeläge erneuert"
    )
    elektroinstallation_erneuert = models.BooleanField(
        default=False, verbose_name="Elektroinstallation erneuert"
    )
    energetisch_saniert = models.BooleanField(
        default=False, verbose_name="Energetisch saniert"
    )
    fussbodenheizung = models.BooleanField(
        default=False, verbose_name="Fußbodenheizung"
    )
    offene_kueche = models.BooleanField(default=False, verbose_name="Offene Küche")

    # Calculation-Related Fields
    gesamtpunktzahl = models.IntegerField(
        blank=True, null=True, verbose_name="Gesamtpunktzahl der Wohnung"
    )
    rechenweg_basismiete = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Rechenweg Basismiete (€/qm)",
    )

    def calculate_rent(self):
        """
        Calculates the rent based on the Mietspiegel data.
        """
        if self.rechenweg_basismiete is None or self.gesamtpunktzahl is None:
            return None  # Or raise an exception, depending on your needs

        # Calculate Spannenmitte (€/qm)
        punkte_faktor = (self.gesamtpunktzahl + 100) / 100
        spannenmitte_qm = self.rechenweg_basismiete * punkte_faktor
        self.spannenmitte_qm = round(spannenmitte_qm, 2)

        # You'll need to determine the logic for calculating
        # mietpreisspanne_min_qm and mietpreisspanne_max_qm based on
        # the specific Mietspiegel rules.  This is a placeholder.
        # Example:  Assume a +/- 15% range around the Spannenmitte
        spanne_percentage = 0.15
        self.mietpreisspanne_min_qm = round(
            self.spannenmitte_qm * (1 - spanne_percentage), 2
        )
        self.mietpreisspanne_max_qm = round(
            self.spannenmitte_qm * (1 + spanne_percentage), 2
        )

        # Calculate Gesamtmiete (Spannenmitte)
        self.gesamtmiete_spannenmitte = int(self.spannenmitte_qm * self.wohnflaeche_qm)

        # Calculate Gesamtmiete (Spanne)
        self.gesamtmiete_spanne_min = int(
            self.mietpreisspanne_min_qm * self.wohnflaeche_qm
        )
        self.gesamtmiete_spanne_max = int(
            self.mietpreisspanne_max_qm * self.wohnflaeche_qm
        )

        self.save()  # Save the calculated values

        return {
            "spannenmitte_qm": self.spannenmitte_qm,
            "mietpreisspanne_min_qm": self.mietpreisspanne_min_qm,
            "mietpreisspanne_max_qm": self.mietpreisspanne_max_qm,
            "gesamtmiete_spannenmitte": self.gesamtmiete_spannenmitte,
            "gesamtmiete_spanne_min": self.gesamtmiete_spanne_min,
            "gesamtmiete_spanne_max": self.gesamtmiete_spanne_max,
        }

    def __str__(self):
        return f"Mietspiegel: {self.wohnflaeche_qm} qm, Baujahr {self.baujahr}, Zone {self.zone}"
