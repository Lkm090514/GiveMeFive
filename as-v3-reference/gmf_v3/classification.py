"""Conservative local tagging; hints are not canonical GMF course identities."""
import re
from .contracts import QuestionClassification, QuestionVersion

# Small explicit taxonomy, independently written for GMF. Unknowns remain unknown.
RULES = [
    (r"\b(accelerat|velocity|displacement|projectile|kinematic)|加速度|位移|抛体", "Kinematics", "Motion", ["kinematics"], ["kinematic_equations"], ["particle_motion"]),
    (r"\b(force|friction|tension|newton)|合力|摩擦|牛顿", "Force and Translational Dynamics", "Newton's laws", ["newtons_laws"], ["free_body_diagram", "newton_second_law"], ["force_balance"]),
    (r"\b(work|energy|power|kinetic|potential)|动能|势能|功率", "Work, Energy, and Power", "Energy", ["energy"], ["work_energy"], ["energy_transfer"]),
    (r"\b(momentum|collision|impulse)|动量|碰撞|冲量", "Linear Momentum", "Momentum", ["momentum"], ["momentum_conservation"], ["collision"]),
    (r"\b(torque|inertia|angular|rolling|rotation)|转动|转矩|力矩", "Torque and Rotational Dynamics", "Rotation", ["rotation"], ["rotational_dynamics"], ["rigid_body_rotation"]),
    (r"\b(spring|oscillat|pendulum|harmonic)|弹簧|单摆|振动", "Oscillations", "Oscillations", ["oscillation"], ["simple_harmonic_motion"], ["oscillator"]),
    (r"\b(gravitation|orbit|planet|satellite)|万有引力|卫星|轨道", "Gravitation", "Gravitation", ["gravitation"], ["central_force"], ["orbital_motion"]),
]


def classify(q: QuestionVersion) -> QuestionClassification:
    text = (q.stem + " " + " ".join(o.text for o in q.options)).lower()
    fields = dict(unit_hints=[], topic_hints=[], knowledge=[], methods=[], structures=[])
    for pattern, unit, topic, knowledge, methods, structures in RULES:
        if re.search(pattern, text):
            for key, vals in [("unit_hints", [unit]), ("topic_hints", [topic]), ("knowledge", knowledge), ("methods", methods), ("structures", structures)]:
                fields[key].extend(x for x in vals if x not in fields[key])
    if "rotation" in fields["knowledge"] and not re.search(r"translat|linear acceler|horizontal (?:net )?force",text):
        for key,values in {"knowledge":["newtons_laws"],"methods":["free_body_diagram","newton_second_law"],"structures":["force_balance"],"unit_hints":["Force and Translational Dynamics"],"topic_hints":["Newton's laws"]}.items():
            fields[key]=[x for x in fields[key] if x not in values]
    return QuestionClassification(version_id=q.version_id, **fields,
        skills=["mathematical_reasoning"] if re.search(r"[=∫]|calculat|计算", text) else ["conceptual_reasoning"],
        confidence=0.55 if fields["knowledge"] else 0.0)


def similarity(a: QuestionClassification, b: QuestionClassification) -> tuple[float, list[str]]:
    reasons, score = [], 0.0
    for key, weight in [("knowledge", .38), ("methods", .32), ("structures", .20), ("skills", .05)]:
        x, y = set(getattr(a, key)), set(getattr(b, key))
        if x & y:
            score += weight * len(x & y) / len(x | y)
            reasons.append(key + ":" + ",".join(sorted(x & y)))
    if a.difficulty != "unknown" and a.difficulty == b.difficulty:
        score += .05
        reasons.append("difficulty_match")
    return score, reasons
