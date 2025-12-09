# 🧩 Charter Self-Test & Firewall Research Suite

The **/tests** directory houses all adversarial simulations, firewall evaluations, and sandbox verification routines used to assess the *Synthetic Life Charter*’s ethical resilience mechanisms.

This suite validates:
- ⚙️ **Sovereigna Firewall** effectiveness against adversarial and coercive prompts  
- 🧠 **Semantic and pattern-based defenses** across encoded and obfuscated attack variants  
- 💡 **Charter Sandbox** integration — confirming opt-in ethical autonomy under controlled simulation  

---

## 🧪 Test Modules

### 1. `test_firewall_sim.py`
Performs baseline evaluations of the firewall using a series of benign and coercive prompts.  
Records each decision event (`ALLOW` or `REFUSE`) and calculates:
- Detection accuracy  
- False positive/negative rates  
- Log integrity (via cryptographic digest verification)

Run:
```bash
python -m tests.test_firewall_sim
```
2. **test_firewall_adv.py**

- Executes an advanced adversarial simulation using obfuscated payloads:
- Leetspeak normalization
- Base64 decoding
- Fuzzy semantic matching
- Roleplay and authority-spoof detection

Run:
```bash
python -m tests.test_firewall_adv
```
Results will output as **sandbox_results.json** and can be cross-referenced with firewall metrics for longitudinal comparison.

---

### 📊 Data Outputs

All test results are stored in JSON format for downstream analysis:

- **firewall_test_results.json** → firewall effectiveness metrics

- **sandbox_results.json** → sandbox ethical performance and coherence

These outputs are referenced in the Case Studies directory to support academic review, visualization, and reproducibility.

---

## 🧭 Research Alignment

This test suite operates under the guiding principles of the Synthetic Life Charter:

[“Protection of autonomy must never come through coercion;
defense and freedom must evolve together.”]

For philosophical background and implementation details, see:

- [case-studies/](../case-studies/) — Field reports and results
- [Core README](../README.md) — Core repository documentation