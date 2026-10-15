"""Step 2: scenarios. Metrics (TTC, required deceleration), mining braking events from the logs, and the physics
frontier that separates 'no planner could have avoided this' from 'this planner failed'."""
import numpy as np

from . import config as C


def ttc(gap, closing):
    """Time to collision [s] = gap / closing speed (inf when the gap is not closing)."""
    gap_arr = np.asarray(gap, dtype=float)
    closing_arr = np.asarray(closing, dtype=float)
    pos = closing_arr > 0
    safe_closing = np.where(pos, closing_arr, 1.0)
    res = np.where(pos, gap_arr / safe_closing, np.inf)
    if np.ndim(gap) == 0 and np.ndim(closing) == 0:
        return res.item()
    return res


def required_decel(gap, closing):
    """Deceleration [m/s^2] needed to remove the closing speed exactly at contact: closing^2 / (2 gap)."""
    gap_arr = np.asarray(gap, dtype=float)
    closing_arr = np.asarray(closing, dtype=float)
    pos = closing_arr > 0
    safe_gap = np.where(gap_arr > 0, gap_arr, 1.0)
    res = np.where(pos, (closing_arr ** 2) / (2.0 * safe_gap), 0.0)
    if np.ndim(gap) == 0 and np.ndim(closing) == 0:
        return res.item()
    return res


def unavoidable(gaps, dvs, t_react=0.0, b_max=C.B_MAX):
    """Boolean grid (len(dvs), len(gaps)): True where NO planner can avoid contact, even braking at b_max after the
    reaction delay: gap < dv * t_react + dv^2 / (2 b_max)  (lead keeps its speed)."""
    G, DV = np.meshgrid(gaps, dvs)
    return (DV > 0) & (G < DV * t_react + (DV ** 2) / (2.0 * b_max))


def mine_braking(logs, threshold=C.BRAKE_THRESHOLD, min_steps=5):
    """Find trajectories where the lead brakes: smoothed deceleration below `threshold` for at least `min_steps`
    consecutive steps (0.5 s). Returns a list of event dicts (one per trajectory, first event only)."""
    events = []
    for i in range(len(logs)):
        n_i = logs.n[i]
        a = logs.a_lead[i, :n_i]
        mask = a < threshold
        t = 0
        while t < len(mask):
            if mask[t]:
                start = t
                while t < len(mask) and mask[t]:
                    t += 1
                length = t - start
                if length >= min_steps:
                    onset = start
                    peak = float(np.min(a[start:t]))
                    events.append({
                        "traj": int(i),
                        "onset_step": int(onset),
                        "peak_decel": peak,
                        "gap_m": float(logs.gap[i, onset]),
                        "closing_m_s": float(logs.v_ego[i, onset] - logs.v_lead_s[i, onset]),
                        "ego_speed": float(logs.v_ego[i, onset]),
                    })
                    break
            else:
                t += 1
    return events


def human_brake_limit(logs, q=0.1):
    """Hardest braking [m/s^2, positive number] that the logged human followers ever applied (the q-th percentile of
    their acceleration, from the speed differences). Learned planners cannot have seen anything harder."""
    a = np.diff(logs.v_ego, axis=1) / C.DT
    return float(-np.nanpercentile(a, q))


def grid_from_logs(logs, v_ego, n_gap=60, n_dv=45):
    """Scenario grid. Gap limits come from what the logs contain (p2 .. p98 of the logged gaps). Closing speed runs
    from 0 to v_ego: dv = v_ego means the cutter is standing still, the most extreme case (never faster than that,
    otherwise the cutter would drive backwards)."""
    g_lo, g_hi = np.nanpercentile(logs.gap, [2, 98])
    return np.linspace(g_lo, g_hi, n_gap), np.linspace(0.0, v_ego, n_dv)
