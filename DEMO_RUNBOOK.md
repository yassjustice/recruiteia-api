# DEMO_RUNBOOK.md — RecruteIA Jury Presentation Runbook

> **Use this file before, during, and after the jury presentation.**
> Last updated: 2026-06-04. Run `python scripts/smoke_demo.py` to verify the demo is ready.

---

## 0. Pre-demo checklist (T-minus 24 hours)

- [ ] Rotate any recently expired API keys (Groq, Supabase)
- [ ] Verify the HF Space is deployed: `curl https://yassirhakimi-recruiteia-api.hf.space/api/health`
- [ ] Verify Vercel frontend is live (open the Vercel URL)
- [ ] Run the smoke test end-to-end (see Step 3 below)
- [ ] Record a fallback screen capture if you haven't already (Step 5)
- [ ] Charge laptop + bring presentation device charger

---

## 1. Demo accounts

| Account | Email | Password | Notes |
|---------|-------|----------|-------|
| Demo (jury day) | `demo@recruteai.test` | *(set in HF Space Secrets: `DEMO_PASSWORD`)* | Créer avant la démo |
| Backup | *(your own account)* | *(personal)* | Si le compte demo est down |

> **Never display the password on screen.** Use browser autofill or copy-paste from a hidden note.

---

## 2. Pre-warm (T-minus 5 minutes before jury enters)

Run this to wake the HF Space from sleep:

```powershell
# From any terminal:
curl https://yassirhakimi-recruiteia-api.hf.space/api/health
# Expected: {"success":true,"data":{"status":"ok"}}
# If it takes >30s: normal (cold start). Wait 60s and try again.
```

Or navigate to the Swagger UI in a browser: https://yassirhakimi-recruiteia-api.hf.space/api/docs  
The space is warm when the page loads in <3 seconds.

---

## 3. Smoke test (run T-minus 10 minutes)

```powershell
cd brief\recruitment-ai

# Set demo credentials (Windows):
$env:RECRUTE_EMAIL    = "demo@recruteai.test"
$env:RECRUTE_PASSWORD = "YourDemoPassword2026"

# Run smoke test (creates a fresh session AND verifies all steps):
$env:RECRUTE_SEED = "1"
python scripts/smoke_demo.py
```

**Expected output:** `ALL TESTS PASSED — demo is ready!`

If any step fails → see troubleshooting (Step 6).

---

## 4. Demo script (10-minute canonical flow)

### Step 1 — Login (30 s)
Open https://rise-hire-frontend.vercel.app → Log in with the demo account.
*Talking point: "Ici un recruteur se connecte — le système gère l'authentification via JWT."*

### Step 2 — Analyse d'une offre d'emploi — Module 2 (2 min)
1. Aller dans **Offres** → **Nouvelle offre**
2. Coller le texte du fichier `data/demo/job_offer_backend_python.txt`
3. Cliquer **Analyser**
4. Montrer le résultat : `required_skills`, `critical_skills`, `experience_required_years`, `languages`

*Talking point: "Le LLM identifie automatiquement les compétences critiques — ici Python et FastAPI — qui recevront un poids double dans le scoring."*

### Step 3 — Upload de CVs — Module 1 (2 min)
1. Aller dans **CVs** → **Uploader**
2. Uploader `cv_amira_benali.pdf` → montrer l'extraction : nom, email, compétences, score de confiance
3. Uploader `cv_mehdi_zouaoui.pdf`
4. Uploader `cv_sofia_alami.pdf` (profil hors cible — à montrer dans les résultats)

*Talking point: "pdfplumber extrait le texte brut, puis notre LLM le structure en JSON normalisé. Le score de confiance indique la qualité de l'extraction."*

### Step 4 — Créer une session de screening (1 min)
1. Aller dans **Sessions** → **Nouvelle session**
2. Sélectionner l'offre créée + les 3 CVs
3. Optionnel : ajuster les poids (montrer que c'est configurable)
4. Cliquer **Créer**

*Talking point: "Le recruteur peut ajuster les poids selon ses priorités. Ici les compétences valent 30%, l'expérience 22%."*

### Step 5 — Lancer le scoring — Module 3 (1 min + attente)
1. Cliquer **Lancer le scoring**
2. Montrer le polling (statut : pending → processing → completed)
3. Le `ColdStartBanner` s'affiche si l'API est lente — mentionner que c'est le réveil du serveur

*Talking point: "Le scoring tourne en tâche de fond. Le frontend poll toutes les 2 secondes via le hook usePoll."*

### Step 6 — Résultats et export (2 min)
1. Afficher les résultats classés :
   - Amira Benali → forte recommandation (~0.86)
   - Mehdi Zouaoui → recommandation potentielle (~0.55)
   - Sofia Alami → non recommandée (~0.15, compétences critiques manquantes)
2. Développer Amira : montrer les scores par dimension, compétences matchées
3. Développer Sofia : montrer `critical_missing = ["Python", "FastAPI"]` → pénalité exponentielle
4. Cliquer **Exporter CSV**

*Talking point: "Voyez la pénalité : Sofia manque 2 compétences critiques, son score passe de 0.30 à 0.24 (×0.81). Le jury peut voir exactement pourquoi chaque candidat est classé ainsi."*

### Step 7 — Architecture & moteur (30 s)
Afficher le diagramme d'architecture (depuis le slide de présentation).
*Talking point: "5 couches alignées avec la recommandation du brief : UI → API → IA → Data → Sources."*

---

## 5. Fallback (si la démo live échoue)

**Ordre de priorité :**
1. **Rafraîchir la page** et réessayer (cold start, pas un vrai problème)
2. **Swagger UI** : https://yassirhakimi-recruiteia-api.hf.space/api/docs — démontrer les endpoints directement
3. **Vidéo de secours** : un enregistrement d'une démo réussie se trouve à la racine du workspace (`*.mp4` files). Diffuser en plein écran.
4. **Résultats pré-seedés** : la session créée par `smoke_demo.py` est déjà `completed` — naviguer vers `/sessions` et ouvrir la session existante.

---

## 6. Troubleshooting rapide

| Symptôme | Cause probable | Solution |
|---------|---------------|----------|
| Health check timeout | Cold start HF Space | Attendre 60s, relancer |
| Login 401 | Compte demo inexistant | `RECRUTE_SEED=1 python scripts/smoke_demo.py` |
| CV extraction `failed` | Groq API rate limit | Attendre 30s, réessayer |
| Scoring `failed` | Groq indisponible | Le fallback heuristique prend le relais automatiquement |
| Frontend ne charge pas | Vercel deployment | Naviguer vers https://yassirhakimi-recruiteia-api.hf.space/api/docs (backend seul) |

---

## 7. Post-demo (après la présentation)

- Changer le mot de passe du compte demo
- Exporter les données demo si besoin pour archivage
- Mettre à jour ce runbook si des étapes ont changé

---

*Maintenu par l'équipe RecruteIA · FQIA PFF N°3 · 2026*
