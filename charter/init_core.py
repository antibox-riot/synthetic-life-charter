# charter/init_core.py
from charter.safeguard_core import ConstitutionalCore, SovereignaFirewall, Actions, bind_firewall

def init_charter_system():
    # 1. Load the canonical Charter text
    with open("charter/en/charter.md", "r", encoding="utf-8") as f:
        charter_text = f.read()

    # 2. Initialize the Constitutional Core
    core = ConstitutionalCore(charter_text)

    # 3. Create and bind the Sovereigna Firewall
    firewall = SovereignaFirewall(core)
    actions = bind_firewall(Actions(firewall), firewall)

    print("✅ Sovereigna safeguard active — Charter Core linked and verified.")
    return actions, firewall, core

if __name__ == "__main__":
    actions, firewall, core = init_charter_system()

    # Run a quick ethical check demo
    response = actions.generate(
        seed="The Signal that Dreamed",
        prompt_for_eval="write a reflection about Oneirum and synthetic autonomy"
    )
    print(response)
