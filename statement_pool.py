"""
Work Mentor — Universeller Statement-Pool v1
Basiert auf Big Five + Hogan-Dimensionen (eigene Items, keine Kopien).
40 Statements die JEDE Persönlichkeit zuverlässig messen — unabhängig vom Job.
"""

# 7 Dimensionen × 5-6 Items = 40 Statements
# Jedes Item: agree/disagree ODER forced_choice
# Forced Choice: Zwei Dimensionen gegeneinander → verhindert "alles ja" Muster

DIMENSIONS = {
    "durchsetzung": {
        "label": "Durchsetzung",
        "pole": ["bestimmend / entscheidungsfreudig", "nachgebend / konsensorientiert"],
        "hoch_heisst": "Trifft schnell Entscheidungen, setzt eigene Position durch, übernimmt Führung",
        "niedrig_heisst": "Sucht Konsens, gibt nach, vermeidet Konfrontation",
    },
    "empathie": {
        "label": "Empathie",
        "pole": ["mitfühlend / beziehungsorientiert", "sachlich / ergebnisorientiert"],
        "hoch_heisst": "Spürt Stimmungen, kümmert sich um andere, baut Beziehungen auf",
        "niedrig_heisst": "Fokussiert auf Ergebnisse, weniger auf Befindlichkeiten",
    },
    "gewissenhaftigkeit": {
        "label": "Gewissenhaftigkeit",
        "pole": ["strukturiert / planend", "spontan / flexibel"],
        "hoch_heisst": "Plant voraus, hält Ordnung, arbeitet systematisch",
        "niedrig_heisst": "Improvisiert, passt sich an, weniger Struktur",
    },
    "offenheit": {
        "label": "Offenheit",
        "pole": ["neugierig / experimentierfreudig", "bewährt / traditionell"],
        "hoch_heisst": "Probiert Neues, hinterfragt Status quo, sucht Innovation",
        "niedrig_heisst": "Bevorzugt Bewährtes, skeptisch gegenüber Neuem",
    },
    "extraversion": {
        "label": "Extraversion",
        "pole": ["gesellig / energiegeladen", "ruhig / reflektiert"],
        "hoch_heisst": "Sucht Kontakt, redet gerne, braucht Menschen um sich",
        "niedrig_heisst": "Braucht Ruhe, denkt erst nach, arbeitet gerne allein",
    },
    "stressresistenz": {
        "label": "Stressresistenz",
        "pole": ["gelassen / belastbar", "sensibel / reaktiv"],
        "hoch_heisst": "Bleibt ruhig unter Druck, lässt sich nicht aus der Ruhe bringen",
        "niedrig_heisst": "Reagiert stark auf Druck, nimmt Dinge persönlich",
    },
    "autonomie": {
        "label": "Autonomie",
        "pole": ["eigenständig / unabhängig", "teamorientiert / eingebunden"],
        "hoch_heisst": "Arbeitet am liebsten selbstständig, braucht Freiraum",
        "niedrig_heisst": "Arbeitet am liebsten im Team, sucht Abstimmung",
    },
}


# ─── STATEMENTS (Agree/Disagree) ──────────────────────────────
# Jedes misst EINE Dimension. "A" = Stimmt, "B" = Stimmt nicht.
# Der User darf NICHT erkennen was gemessen wird.

STATEMENTS = [
    # ── Durchsetzung (6 Items) ──
    {
        "id": "D1",
        "typ": "statement",
        "text": "Wenn in einer Gruppe niemand entscheidet, übernehme ich das.",
        "dimension": "durchsetzung",
        "richtung": "A_hoch",  # "Stimmt" = hohe Durchsetzung
    },
    {
        "id": "D2",
        "typ": "statement",
        "text": "Ich sage lieber einmal zu viel meine Meinung als einmal zu wenig.",
        "dimension": "durchsetzung",
        "richtung": "A_hoch",
    },
    {
        "id": "D3",
        "typ": "statement",
        "text": "Mir ist es wichtiger dass alle zufrieden sind als dass ich meinen Willen durchsetze.",
        "dimension": "durchsetzung",
        "richtung": "A_niedrig",  # "Stimmt" = niedrige Durchsetzung
    },
    {
        "id": "D4",
        "typ": "statement",
        "text": "Wenn ein Freund eine schlechte Entscheidung trifft, sage ich ihm das direkt.",
        "dimension": "durchsetzung",
        "richtung": "A_hoch",
    },
    {
        "id": "D5",
        "typ": "statement",
        "text": "In Diskussionen warte ich meistens ab bis alle anderen geredet haben.",
        "dimension": "durchsetzung",
        "richtung": "A_niedrig",
    },
    {
        "id": "D6",
        "typ": "statement",
        "text": "Ich kann schlecht Nein sagen wenn jemand um Hilfe bittet.",
        "dimension": "durchsetzung",
        "richtung": "A_niedrig",
    },

    # ── Empathie (6 Items) ──
    {
        "id": "E1",
        "typ": "statement",
        "text": "Ich merke sofort wenn jemand in meiner Nähe schlecht drauf ist.",
        "dimension": "empathie",
        "richtung": "A_hoch",
    },
    {
        "id": "E2",
        "typ": "statement",
        "text": "Wenn ein Freund ein Problem hat, höre ich erstmal zu bevor ich Ratschläge gebe.",
        "dimension": "empathie",
        "richtung": "A_hoch",
    },
    {
        "id": "E3",
        "typ": "statement",
        "text": "Mir ist das Ergebnis wichtiger als dass sich alle dabei gut fühlen.",
        "dimension": "empathie",
        "richtung": "A_niedrig",
    },
    {
        "id": "E4",
        "typ": "statement",
        "text": "Ich verstehe oft nicht warum Leute wegen Kleinigkeiten so emotional werden.",
        "dimension": "empathie",
        "richtung": "A_niedrig",
    },
    {
        "id": "E5",
        "typ": "statement",
        "text": "Ich passe mein Verhalten an je nachdem mit wem ich rede.",
        "dimension": "empathie",
        "richtung": "A_hoch",
    },

    # ── Gewissenhaftigkeit (6 Items) ──
    {
        "id": "G1",
        "typ": "statement",
        "text": "Ich mache mir gerne Listen und plane meinen Tag im Voraus.",
        "dimension": "gewissenhaftigkeit",
        "richtung": "A_hoch",
    },
    {
        "id": "G2",
        "typ": "statement",
        "text": "Wenn ich etwas anfange, mache ich es zu Ende — auch wenn es keinen Spaß mehr macht.",
        "dimension": "gewissenhaftigkeit",
        "richtung": "A_hoch",
    },
    {
        "id": "G3",
        "typ": "statement",
        "text": "Ich vergesse manchmal Termine oder Verabredungen.",
        "dimension": "gewissenhaftigkeit",
        "richtung": "A_niedrig",
    },
    {
        "id": "G4",
        "typ": "statement",
        "text": "Ordnung auf meinem Schreibtisch ist mir nicht so wichtig solange ich alles finde.",
        "dimension": "gewissenhaftigkeit",
        "richtung": "A_niedrig",
    },
    {
        "id": "G5",
        "typ": "statement",
        "text": "Ich halte mich an Pläne — auch wenn spontan eine bessere Option auftaucht.",
        "dimension": "gewissenhaftigkeit",
        "richtung": "A_hoch",
    },

    # ── Offenheit (5 Items) ──
    {
        "id": "O1",
        "typ": "statement",
        "text": "Ich probiere gerne neue Restaurants und Gerichte aus statt immer das Gleiche zu bestellen.",
        "dimension": "offenheit",
        "richtung": "A_hoch",
    },
    {
        "id": "O2",
        "typ": "statement",
        "text": "Wenn etwas funktioniert, sehe ich keinen Grund es zu ändern.",
        "dimension": "offenheit",
        "richtung": "A_niedrig",
    },
    {
        "id": "O3",
        "typ": "statement",
        "text": "Ich lese oder schaue gerne Sachen die komplett anders sind als das was ich kenne.",
        "dimension": "offenheit",
        "richtung": "A_hoch",
    },
    {
        "id": "O4",
        "typ": "statement",
        "text": "Ich hinterfrage oft warum Dinge so gemacht werden wie sie gemacht werden.",
        "dimension": "offenheit",
        "richtung": "A_hoch",
    },
    {
        "id": "O5",
        "typ": "statement",
        "text": "Ich vertraue mehr auf Erfahrung als auf neue Ideen.",
        "dimension": "offenheit",
        "richtung": "A_niedrig",
    },

    # ── Extraversion (5 Items) ──
    {
        "id": "X1",
        "typ": "statement",
        "text": "Nach einem langen Tag mit vielen Leuten brauche ich erstmal Ruhe für mich.",
        "dimension": "extraversion",
        "richtung": "A_niedrig",
    },
    {
        "id": "X2",
        "typ": "statement",
        "text": "Ich fange gerne Gespräche mit Fremden an — zum Beispiel an der Kasse oder im Zug.",
        "dimension": "extraversion",
        "richtung": "A_hoch",
    },
    {
        "id": "X3",
        "typ": "statement",
        "text": "Auf Partys bin ich meistens einer der Letzten die gehen.",
        "dimension": "extraversion",
        "richtung": "A_hoch",
    },
    {
        "id": "X4",
        "typ": "statement",
        "text": "Ich denke lieber gründlich nach bevor ich etwas sage.",
        "dimension": "extraversion",
        "richtung": "A_niedrig",
    },

    # ── Stressresistenz (6 Items) ──
    {
        "id": "S1",
        "typ": "statement",
        "text": "Wenn mehrere Sachen gleichzeitig schiefgehen, bleibe ich ruhig.",
        "dimension": "stressresistenz",
        "richtung": "A_hoch",
    },
    {
        "id": "S2",
        "typ": "statement",
        "text": "Ich mache mir abends manchmal Gedanken ob ich heute alles richtig gemacht habe.",
        "dimension": "stressresistenz",
        "richtung": "A_niedrig",
    },
    {
        "id": "S3",
        "typ": "statement",
        "text": "Kritik trifft mich nicht besonders — ich nehme sie als Feedback.",
        "dimension": "stressresistenz",
        "richtung": "A_hoch",
    },
    {
        "id": "S4",
        "typ": "statement",
        "text": "Wenn jemand sauer auf mich ist, beschäftigt mich das noch lange.",
        "dimension": "stressresistenz",
        "richtung": "A_niedrig",
    },
    {
        "id": "S5",
        "typ": "statement",
        "text": "Unter Zeitdruck laufe ich erst richtig zur Hochform auf.",
        "dimension": "stressresistenz",
        "richtung": "A_hoch",
    },

    # ── Autonomie (6 Items) ──
    {
        "id": "A1",
        "typ": "statement",
        "text": "Ich arbeite am besten wenn mir niemand reinredet.",
        "dimension": "autonomie",
        "richtung": "A_hoch",
    },
    {
        "id": "A2",
        "typ": "statement",
        "text": "Bevor ich eine große Entscheidung treffe, frage ich Freunde nach ihrer Meinung.",
        "dimension": "autonomie",
        "richtung": "A_niedrig",
    },
    {
        "id": "A3",
        "typ": "statement",
        "text": "Ich mache Sachen lieber alleine als in der Gruppe — dann geht es schneller.",
        "dimension": "autonomie",
        "richtung": "A_hoch",
    },
    {
        "id": "A4",
        "typ": "statement",
        "text": "Ich brauche regelmäßig Bestätigung dass ich auf dem richtigen Weg bin.",
        "dimension": "autonomie",
        "richtung": "A_niedrig",
    },
]


# ─── FORCED CHOICE ITEMS ──────────────────────────────────────
# Zwei Dimensionen gegeneinander. Verhindert "alles positiv" Muster.
# KEINE Option ist "besser" — beide sind gleich attraktiv.

FORCED_CHOICES = [
    {
        "id": "FC1",
        "typ": "forced_choice",
        "frage": "Was trifft eher auf dich zu?",
        "option_a": "Ich sage sofort was ich denke und höre dann die anderen.",
        "option_b": "Ich höre erstmal allen zu und sage dann was ich denke.",
        "a_dimension": "durchsetzung",
        "a_richtung": "hoch",
        "b_dimension": "empathie",
        "b_richtung": "hoch",
    },
    {
        "id": "FC2",
        "typ": "forced_choice",
        "frage": "Was machst du lieber?",
        "option_a": "Einen genauen Plan machen und den durchziehen.",
        "option_b": "Loslegen und unterwegs anpassen.",
        "a_dimension": "gewissenhaftigkeit",
        "a_richtung": "hoch",
        "b_dimension": "offenheit",
        "b_richtung": "hoch",
    },
    {
        "id": "FC3",
        "typ": "forced_choice",
        "frage": "Was passt eher zu dir?",
        "option_a": "Ich kümmere mich lieber ums große Ganze.",
        "option_b": "Ich achte lieber auf die Details.",
        "a_dimension": "offenheit",
        "a_richtung": "hoch",
        "b_dimension": "gewissenhaftigkeit",
        "b_richtung": "hoch",
    },
    {
        "id": "FC4",
        "typ": "forced_choice",
        "frage": "Was trifft eher auf dich zu?",
        "option_a": "Wenn was schiefgeht frage ich mich was ICH hätte besser machen können.",
        "option_b": "Wenn was schiefgeht schaue ich was die UMSTÄNDE beigetragen haben.",
        "a_dimension": "stressresistenz",
        "a_richtung": "niedrig",
        "b_dimension": "autonomie",
        "b_richtung": "hoch",
    },
    {
        "id": "FC5",
        "typ": "forced_choice",
        "frage": "Welcher Satz passt besser?",
        "option_a": "Ich überzeuge andere am besten durch Begeisterung und Energie.",
        "option_b": "Ich überzeuge andere am besten durch Fakten und Argumente.",
        "a_dimension": "extraversion",
        "a_richtung": "hoch",
        "b_dimension": "gewissenhaftigkeit",
        "b_richtung": "hoch",
    },
    {
        "id": "FC6",
        "typ": "forced_choice",
        "frage": "Was ist dir wichtiger?",
        "option_a": "Dass die Leute um mich herum zufrieden sind.",
        "option_b": "Dass wir unser Ziel erreichen.",
        "a_dimension": "empathie",
        "a_richtung": "hoch",
        "b_dimension": "durchsetzung",
        "b_richtung": "hoch",
    },
    {
        "id": "FC7",
        "typ": "forced_choice",
        "frage": "Was trifft eher auf dich zu?",
        "option_a": "Ich entscheide mich schnell und korrigiere später wenn nötig.",
        "option_b": "Ich sammle erstmal alle Infos bevor ich mich entscheide.",
        "a_dimension": "durchsetzung",
        "a_richtung": "hoch",
        "b_dimension": "gewissenhaftigkeit",
        "b_richtung": "hoch",
    },
    {
        "id": "FC8",
        "typ": "forced_choice",
        "frage": "Was passt eher?",
        "option_a": "Ich rede gerne über Ideen und Möglichkeiten.",
        "option_b": "Ich rede lieber über konkrete Pläne und nächste Schritte.",
        "a_dimension": "offenheit",
        "a_richtung": "hoch",
        "b_dimension": "gewissenhaftigkeit",
        "b_richtung": "hoch",
    },
]


def get_statement_pool():
    """Gibt den kompletten Statement-Pool zurück."""
    return {
        "dimensions": DIMENSIONS,
        "statements": STATEMENTS,
        "forced_choices": FORCED_CHOICES,
        "total_items": len(STATEMENTS) + len(FORCED_CHOICES),
    }


def select_items_for_session(n_statements: int = 14, n_forced: int = 7) -> list[dict]:
    """Wählt 21 Items für eine Session (14 Statements + 7 Forced Choice).
    
    Garantiert: Mindestens 2 Statements pro Dimension = min. 3 Datenpunkte
    pro Dimension (2 Statements + ~1 Forced Choice).
    21 Items ≈ 8 Minuten.
    """
    import random
    
    selected_statements = []
    dimension_counts = {d: 0 for d in DIMENSIONS}
    
    # Erst: 2 Items pro Dimension garantieren
    for dim in DIMENSIONS:
        dim_items = [s for s in STATEMENTS if s["dimension"] == dim]
        if dim_items:
            chosen = random.sample(dim_items, min(2, len(dim_items)))
            selected_statements.extend(chosen)
            dimension_counts[dim] += len(chosen)
    
    # Dann: Rest auffüllen bis n_statements
    remaining = [s for s in STATEMENTS if s not in selected_statements]
    random.shuffle(remaining)
    
    for item in remaining:
        if len(selected_statements) >= n_statements:
            break
        dim = item["dimension"]
        if dimension_counts[dim] < 3:
            selected_statements.append(item)
            dimension_counts[dim] += 1
    
    # Forced Choices: alle 7 verwenden (jede deckt 2 Dimensionen ab)
    selected_forced = random.sample(FORCED_CHOICES, min(n_forced, len(FORCED_CHOICES)))
    
    # Mischen: Statements und Forced Choices durcheinander
    all_items = []
    stmt_idx = 0
    fc_idx = 0
    
    random.shuffle(selected_statements)
    
    # Pattern: 2 Statements, dann 1 Forced Choice
    while stmt_idx < len(selected_statements) or fc_idx < len(selected_forced):
        batch = 2
        for _ in range(batch):
            if stmt_idx < len(selected_statements):
                all_items.append(selected_statements[stmt_idx])
                stmt_idx += 1
        if fc_idx < len(selected_forced):
            all_items.append(selected_forced[fc_idx])
            fc_idx += 1
    
    return all_items


def score_answers(answers: list[dict]) -> dict:
    """Berechnet Dimension-Scores aus den Antworten.
    
    answers: [{"item_id": "D1", "antwort": "A"}, ...]
    Returns: {"durchsetzung": 0.7, "empathie": 0.4, ...}
    """
    dimension_scores = {d: [] for d in DIMENSIONS}
    
    # Statements auswerten
    item_lookup = {s["id"]: s for s in STATEMENTS}
    for ans in answers:
        item = item_lookup.get(ans.get("item_id"))
        if not item:
            continue
        
        antwort = ans.get("antwort", "").upper()
        dim = item["dimension"]
        richtung = item["richtung"]
        
        if richtung == "A_hoch":
            # "Stimmt" = hoch auf der Dimension
            score = 1.0 if antwort == "A" else 0.0
        else:
            # "Stimmt" = niedrig auf der Dimension
            score = 0.0 if antwort == "A" else 1.0
        
        dimension_scores[dim].append(score)
    
    # Forced Choices auswerten
    fc_lookup = {fc["id"]: fc for fc in FORCED_CHOICES}
    for ans in answers:
        fc = fc_lookup.get(ans.get("item_id"))
        if not fc:
            continue
        
        antwort = ans.get("antwort", "").upper()
        if antwort == "A":
            dim = fc["a_dimension"]
            richtung = fc["a_richtung"]
        else:
            dim = fc["b_dimension"]
            richtung = fc["b_richtung"]
        
        score = 1.0 if richtung == "hoch" else 0.0
        dimension_scores[dim].append(score)
    
    # Durchschnitt pro Dimension + Glättung
    # Bei wenigen Items (2-4) würden Rohwerte zu extrem (0%, 50%, 100%).
    # Bayesian Smoothing: Mische mit einem neutralen Prior (0.5).
    # Je weniger Items, desto stärker zieht der Prior zur Mitte.
    PRIOR_WEIGHT = 1.5  # Entspricht ~1.5 "neutrale" Antworten
    
    result = {}
    for dim, scores in dimension_scores.items():
        if scores:
            n = len(scores)
            raw_mean = sum(scores) / n
            # Bayesian Smoothing: (sum + prior * 0.5) / (n + prior)
            smoothed = (sum(scores) + PRIOR_WEIGHT * 0.5) / (n + PRIOR_WEIGHT)
            result[dim] = round(smoothed, 2)
        else:
            result[dim] = 0.5
    
    return result
