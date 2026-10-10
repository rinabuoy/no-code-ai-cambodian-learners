#!/usr/bin/env python3
"""Generate original (copyright-free) figures for the textbook into wiki/figures/generated/.
Run: python3 scripts/make_figures.py"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle, Rectangle

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wiki", "figures", "generated")
os.makedirs(OUT, exist_ok=True)
BLUE, RED, GREEN, GREY = "#1F5F8B", "#D9534F", "#2E9E7E", "#8C98A8"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# 1. flower: RGB / grayscale / binary (drawn from scratch)
def flower(size=240):
    y, x = np.mgrid[0:size, 0:size]
    img = np.zeros((size, size, 3))
    img[:] = (0.78, 0.9, 0.78)                      # green background
    cx = cy = size / 2
    for k in range(8):                              # petals
        a = k * np.pi / 4
        px, py = cx + 55 * np.cos(a), cy + 55 * np.sin(a)
        d = ((x - px) * np.cos(a) + (y - py) * np.sin(a)) ** 2 / 45 ** 2 + (-(x - px) * np.sin(a) + (y - py) * np.cos(a)) ** 2 / 24 ** 2
        img[d < 1] = (0.9, 0.2, 0.3)
    img[((x - cx) ** 2 + (y - cy) ** 2) < 28 ** 2] = (0.98, 0.8, 0.1)   # centre
    return img


f = flower()
gray = f @ np.array([0.299, 0.587, 0.114])
binary = (gray > 0.62).astype(float)
fig, ax = plt.subplots(1, 3, figsize=(7, 2.6))
for a, im, t, cm in zip(ax, [f, gray, binary], ["RGB (colour)", "Grayscale", "Binary (black / white)"], [None, "gray", "gray"]):
    a.imshow(im, cmap=cm, vmin=0, vmax=1); a.set_title(t); a.axis("off")
save(fig, "flower-image-types.png")

# 2. output bars before / after training
fig, ax = plt.subplots(1, 2, figsize=(7, 2.4), sharey=True)
cls = ["Can", "Plastic", "Paper"]
for a, vals, t in zip(ax, [[31, 38, 31], [100, 0, 0]], ["Before training (a crushed can)", "After training"]):
    a.barh(cls[::-1], vals[::-1], color=[GREEN, RED, BLUE][::-1][::-1][::-1] if False else [BLUE, RED, GREEN])
    a.set_xlim(0, 100); a.set_title(t, fontsize=9); a.set_xlabel("confidence (%)")
    for i, v in enumerate(vals[::-1]): a.text(v + 1.5, i, f"{v}%", va="center", fontsize=8)
save(fig, "training-before-after.png")

# 3. epochs: too few / about right / too many (illustrative)
e = np.linspace(0, 100, 200)
train = 0.08 + 0.9 * np.exp(-e / 12)
val = train + 0.05 + 0.0030 * np.maximum(e - 30, 0)
fig, ax = plt.subplots(figsize=(5.2, 3))
ax.plot(e, train, color=BLUE, label="error on training pictures")
ax.plot(e, val, color=RED, label="error on new pictures")
ax.axvspan(0, 5, color=GREY, alpha=.2); ax.axvspan(60, 100, color=GREY, alpha=.2)
ax.text(6.5, 0.93, "too few epochs:\nnot enough time to learn", fontsize=7, va="top"); ax.text(62, 0.55, "too many epochs:\nmemorizing the training\npictures", fontsize=7, va="top")
ax.set_xlabel("epochs (illustrative)"); ax.set_ylabel("error"); ax.legend(fontsize=7, loc="upper right", bbox_to_anchor=(1.0, 0.8))
ax.set_ylim(0, 1)
save(fig, "epochs-effect.png")

# 4. confidence: strong vs weak
fig, ax = plt.subplots(1, 2, figsize=(7, 2.3), sharey=True)
cls = ["Yes", "No", "Stop"]
for a, vals, t, col in zip(ax, [[88, 7, 5], [45, 35, 20]], ["Strong model: clear winner (>80%)", "Weak model: unsure (40-60% spread)"], [GREEN, RED]):
    a.barh(cls[::-1], vals[::-1], color=col); a.set_xlim(0, 100); a.set_title(t, fontsize=9); a.set_xlabel("confidence (%)")
    for i, v in enumerate(vals[::-1]): a.text(v + 1.5, i, f"{v}%", va="center", fontsize=8)
save(fig, "confidence-strong-weak.png")

# 5. preview bars (pose)
fig, ax = plt.subplots(figsize=(4.2, 2))
cls, vals = ["Neutral", "Sleepy_Left", "Sleepy_Right"], [92, 5, 3]
ax.barh(cls[::-1], vals[::-1], color=[GREY, GREY, BLUE]); ax.set_xlim(0, 100); ax.set_xlabel("confidence (%) - example values")
for i, v in enumerate(vals[::-1]): ax.text(v + 1.5, i, f"{v}%", va="center", fontsize=8)
save(fig, "pose-preview-bars.png")

# 6. confusion matrix (example from the augmentation lesson)
M = np.array([[9, 1, 0, 0], [3, 7, 0, 0], [0, 0, 8, 2], [0, 0, 1, 9]])
labs = ["en_1", "en_7", "en_3", "en_8"]
fig, ax = plt.subplots(figsize=(4.4, 3.8))
ax.imshow(M, cmap="Blues", vmin=0, vmax=12)
ax.set_xticks(range(4), labs); ax.set_yticks(range(4), labs)
ax.set_xlabel("what the model said"); ax.set_ylabel("the real digit")
for i in range(4):
    for j in range(4):
        ax.text(j, i, M[i, j], ha="center", va="center", color="white" if M[i, j] > 6 else "black", fontsize=11)
    ax.text(4.1, i, f"{M[i,i]*10}%", va="center", fontsize=9, color=BLUE)
ax.text(4.1, -0.75, "class acc.", fontsize=8, color=BLUE)
for s in ax.spines.values(): s.set_visible(False)
save(fig, "confusion-matrix-example.png")

# 7. audio augmentation waveforms (synthetic 'yes')
sr = 4000
t = np.arange(0, 1, 1 / sr)
env = np.exp(-((t - 0.45) / 0.14) ** 2)
yes = env * (np.sin(2 * np.pi * 180 * t) + 0.5 * np.sin(2 * np.pi * 540 * t * (1 + 0.15 * t)))
yes /= np.abs(yes).max()


def speed(x, f):
    tt = np.arange(0, 1, 1 / sr) * f
    y = np.interp(tt, np.arange(len(x)) / sr, x, right=0)
    return y


def shift(x, frac):
    n = int(len(x) * frac); y = np.roll(x, n)
    if n > 0: y[:n] = 0
    else: y[n:] = 0
    return y


rng = np.random.default_rng(3)
def noise(x, db):
    p = np.mean(x ** 2) ** .5
    return x + rng.normal(0, p * 10 ** (-db / 20), len(x))

items = [("original", yes), ("speed x1.15 (faster)", speed(yes, 1.15)), ("speed x0.85 (slower)", speed(yes, 0.85)),
         ("time shift +20%", shift(yes, 0.2)), ("volume x0.5", yes * 0.5), ("volume x1.5", yes * 1.5),
         ("noise 30 dB below", noise(yes, 30)), ("noise 10 dB below", noise(yes, 10))]
fig, axs = plt.subplots(4, 2, figsize=(7, 5.4), sharex=True, sharey=True)
for a, (n, w) in zip(axs.ravel(), items):
    a.plot(t, w, color=BLUE, lw=0.5); a.set_title(n, fontsize=8, pad=2); a.set_ylim(-1.8, 1.8); a.set_yticks([])
for a in axs[-1]: a.set_xlabel("time (s)")
fig.tight_layout()
save(fig, "audio-augmentation-waveforms.png")
print("generated:", sorted(os.listdir(OUT)))
