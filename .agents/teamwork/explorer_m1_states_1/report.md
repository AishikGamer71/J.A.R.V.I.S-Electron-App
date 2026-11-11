# State Machine Dynamics, Damping Physics, and Animation Engine Specification

**Document Version**: 1.0.0  
**Author**: Explorer Agent (`explorer_m1_states_1`)  
**Mission**: Milestone 1 State Machine & Dynamic Animation Physics  
**Authoritative Source**: `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`  
**Target Systems**: `src/components/dashboard/holographic-core/` (`types.ts`, `state-machine.ts`, `constants.ts`, `geometries.ts`) and `src/components/dashboard/sphere.tsx`  
**Date**: November 11, 2026  

---

## 1. Executive Summary

This report establishes the complete, authoritative specification for the **11-State Holographic Core State Machine and Physics Engine** reverse-engineered directly from `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`. 

The visualizer operates as a multi-layer holographic core powered by Three.js / React Three Fiber, featuring:
1. **11 Discrete Cognitive States** with individual color palettes, volumetric core glow dynamics, gyroscopic ring motions, and geometry morphing.
2. **Frame-Rate Independent Exponential Damping** using continuous-time decay formulations ($k = 6.2\text{ s}^{-1}$ for state weights and geometry, $k = 14.0\text{ s}^{-1}$ for audio spectrum smoothing) with safe delta clamping ($\Delta t \le 50\text{ ms}$).
3. **Dual-Pulse Cardiac Shockwave Engine** modeling physical systole and diastole contractions ("lub-dub") alongside state-transition pulse triggers.
4. **Toroidal Poloidal Recirculation & 3D Morphing Targets** transforming a 3D Fibonacci sphere into latitude/longitude wireframe globes, beveled holographic cubes, and continuous Arc-Reactor poloidal flux fields.

---

## 2. Complete Catalog of the 11 Holographic Core States

### State 1: `IDLE`
- **Key Binding**: `[1]`
- **Color Name**: Ice-Cyan
- **Hex Code**: `#67e8f9`
- **RGB Normalized**: `(0.40392, 0.90980, 0.97647)` (8-bit: `103, 232, 249`)
- **Three.Color Representation**: `new THREE.Color('#67e8f9')`
- **Accent / Crest Color**: Pure White `(1.0, 1.0, 1.0)` dynamically blended via crest scalar
- **Backdrop Halo**: Deep navy radial gradient (`rgba(2, 8, 22, 0.88)` to `rgba(0, 0, 0, 0)`)
- **Core Glow Parameters**:
  - Base Scale: $2.45$
  - Scale Modulation: $\text{scale} = 2.45 + w_{\text{IDLE}} \times 0.15 \sin(1.6 t)$ (Range: $[2.30, 2.60]$)
  - Base Opacity: $0.36$
  - Breathing Frequency: $\omega = 1.6\text{ rad/s}$ ($f \approx 0.2546\text{ Hz}$, Period $T \approx 3.927\text{ s}$)
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $0.25$
  - Ring 1 Opacity: $0.22 \times w_{\text{IDLE}}$
  - Ring 2 Opacity: $0.22 \times 0.78 \times w_{\text{IDLE}} \approx 0.1716$
  - Ring 3: Inactive ($\text{opacity} = 0$)
  - Ring 1 Scale: $1.0$
  - Ring 2 Scale: $1.0$
- **3D Scene Orientation & Rotational Drift**:
  - $\Delta \text{rot}_y = dt \times 0.15$
  - $\text{target\_rot}_x = 0.08 \sin(0.4 t)$ (lerped via `damp`)
  - $\Delta \text{rot}_z = dt \times 0.04$
- **Geometry & Particle Displacement**:
  - Geometry Base: Fibonacci Sphere ($\vec{d} = \vec{n}$)
  - Breathing Wave: $\sin(1.6 t) \times 0.035$
  - Surface Wave Turbulence: $\sin(2.5 n_x + 1.1 t) \cos(2.5 n_y - 0.9 t) \times 0.03$
  - Total Displacement Formula:
    $$\text{disp}_{\text{IDLE}} = 0.035 \sin(1.6 t) + 0.03 \sin(2.5 n_x + 1.1 t) \cos(2.5 n_y - 0.9 t)$$
  - Extra Highlight: $0.0$

---

### State 2: `LISTENING`
- **Key Binding**: `[2]`
- **Color Name**: Sky-Cyan
- **Hex Code**: `#00f0ff`
- **RGB Normalized**: `(0.00000, 0.94118, 1.00000)` (8-bit: `0, 240, 255`)
- **Three.Color Representation**: `new THREE.Color('#00f0ff')`
- **Accent / Crest Color**: Intense luminescent cyan-white cresting on ripple waves
- **Core Glow Parameters**:
  - Base Scale: $2.45$
  - Scale Modulation: $\text{scale} = 2.45 + w_{\text{LISTENING}} \times (0.25 + 0.7 \times \text{bass}) = 2.70 + 0.7 \times \text{bass}$
  - Opacity: $0.36$
  - Pulse Mode: Driven by audio bass envelope
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $0.60$
  - Ring 1 Opacity: $0.50 \times w_{\text{LISTENING}}$
  - Ring 2 Opacity: $0.50 \times 0.78 \times w_{\text{LISTENING}} = 0.3900$
  - Ring 3: Inactive ($\text{opacity} = 0$)
  - Ring 1 Scale: $1.0 + w_{\text{LISTENING}} \times 0.08 \times \text{bass}$
  - Ring 2 Scale: $1.0$
- **3D Scene Orientation & Rotational Drift**:
  - $\Delta \text{rot}_y = dt \times 0.18$
  - $\text{target\_rot}_x = 0.08\text{ rad}$ (fixed forward attentiveness)
  - $\text{target\_rot}_z = 0.00\text{ rad}$
- **Geometry & Particle Displacement**:
  - Geometry Base: Fibonacci Sphere ($\vec{d} = \vec{n}$)
  - Radial Inward Contraction: $-0.07$ (physical sphere contraction into focused listening mode)
  - Concentric Sonar Ripples: $0.085 \sin(10.0 |n_y| - 6.5 t)$ (equator-to-pole propagation, spatial wave number $k=10.0\text{ rad/unit}$, phase velocity $v=0.65$)
  - Live Audio Reactivity: $+ 0.24 \times \text{bass} + 0.18 \times \text{mid} \sin(14.0 n_y - 10.0 t)$
  - Total Displacement Formula:
    $$\text{disp}_{\text{LISTENING}} = -0.07 + 0.085 \sin(10.0 |n_y| - 6.5 t) + 0.24 \text{bass} + 0.18 \text{mid} \sin(14.0 n_y - 10.0 t)$$
  - Audio Boost Factor: Live microphone audio inputs are amplified by $2.2\times$
  - Attentive Synthetic Fallback (when total raw audio $< 0.02$):
    $$\text{pulse} = \max(0, 0.5 \sin(3.8 t) + 0.3 \sin(6.3 t))$$
    $$\text{rawBass} = 0.10 + 0.32 \times \text{pulse}, \quad \text{rawMid} = 0.08 + 0.28 \times \text{pulse}, \quad \text{rawTreble} = 0.05 + 0.20 \times \text{pulse}$$

---

### State 3: `THINKING`
- **Key Binding**: `[3]`
- **Color Name**: Amber-Gold
- **Hex Code**: `#fbbf24`
- **RGB Normalized**: `(0.98431, 0.74902, 0.14118)` (8-bit: `251, 191, 36`)
- **Three.Color Representation**: `new THREE.Color('#fbbf24')`
- **Accent / Crest Color**: Hot amber-white filament highlights along harmonic nodal lines
- **Core Glow Parameters**:
  - Scale Modulation: $\text{scale} = 2.45 + w_{\text{THINKING}} \times (0.35 + 0.28 \sin(6.0 t)) = 2.80 + 0.28 \sin(6.0 t)$ (Range: $[2.52, 3.08]$)
  - Opacity Modulation: $\text{opacity} = 0.36 + 0.14 \times w_{\text{THINKING}} = 0.50$ (amplified golden core luminosity)
  - Pulse Frequency: $\omega = 6.0\text{ rad/s}$ ($f \approx 0.9549\text{ Hz}$, Period $T \approx 1.047\text{ s}$)
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $2.40$ (rapid gyro spinning indicative of heavy cognitive processing)
  - Ring 1 Opacity: $0.65 \times w_{\text{THINKING}}$
  - Ring 2 Opacity: $0.65 \times 0.78 \times w_{\text{THINKING}} \approx 0.5070$
  - Ring 3: Inactive ($\text{opacity} = 0$)
  - Ring 1 Scale: $1.0$
  - Ring 2 Scale: $1.0$
- **3D Scene Orientation & Rotational Drift**:
  - Multi-Axis Tumbling:
    $\Delta \text{rot}_y = dt \times 0.72$
    $\Delta \text{rot}_x = dt \times 0.32$
    $\Delta \text{rot}_z = dt \times 0.24$
- **Geometry & Particle Displacement**:
  - Counter-Twisting Hemisphere Vortex:
    $$\text{twist} = w_{\text{THINKING}} \times \left(2.1 n_y \sin(2.0 t) + 0.55 \sin(1.6 t + 0.4 \times \text{phase})\right)$$
    $$d_x = n_x \cos(\text{twist}) - n_z \sin(\text{twist})$$
    $$d_z = n_x \sin(\text{twist}) + n_z \cos(\text{twist})$$
  - 3D Spherical Harmonics Turbulence:
    $$\text{disp}_{\text{THINKING}} = 0.22 \sin(4.0 d_x + 4.5 t) \cos(4.0 d_y - 3.8 t) \sin(4.0 d_z + 3.2 t) + 0.04 \sin(6.0 t + \text{phase})$$

---

### State 4: `SPEAKING`
- **Key Binding**: `[4]`
- **Color Name**: White-Ice
- **Hex Code**: `#e0f2fe`
- **RGB Normalized**: `(0.87843, 0.94902, 0.99608)` (8-bit: `224, 242, 254`)
- **Three.Color Representation**: `new THREE.Color('#e0f2fe')`
- **Accent / Crest Color**: Pure electric white corona cresting ($+0.45 \times \text{bass} \times w_{\text{SPEAKING}}$)
- **Core Glow Parameters**:
  - Scale Modulation: $\text{scale} = 2.45 + w_{\text{SPEAKING}} \times (0.45 + 1.15 \times \text{bass}) = 2.90 + 1.15 \times \text{bass}$ (Range: $[2.90, 4.05]$)
  - Opacity Modulation: $\text{opacity} = 0.36 + w_{\text{SPEAKING}} \times (0.20 + 0.28 \times \text{bass}) = 0.56 + 0.28 \times \text{bass}$ (Range: $[0.56, 0.84]$)
  - Reactivity: Continuous direct coupling to bass audio band
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $0.90$
  - Ring 1 Opacity: $0.55 \times w_{\text{SPEAKING}}$
  - Ring 2 Opacity: $0.55 \times 0.78 \times w_{\text{SPEAKING}} = 0.4290$
  - Ring 3: Inactive ($\text{opacity} = 0$)
  - Ring 1 Scale: $1.0 + w_{\text{SPEAKING}} \times 0.16 \times \text{bass}$
  - Ring 2 Scale: $1.0 + w_{\text{SPEAKING}} \times 0.14 \times \text{mid}$
- **3D Scene Orientation & Rotational Drift**:
  - $\Delta \text{rot}_y = dt \times (0.28 + 0.65 \times \text{bass})$
  - $\text{target\_rot}_x = 0.15 \sin(1.8 t)$
  - $\Delta \text{rot}_z = dt \times 0.08$
- **Geometry & Particle Displacement**:
  - Geometry Base: Fibonacci Sphere ($\vec{d} = \vec{n}$)
  - Acoustic Wave Equation:
    $$\text{disp}_{\text{SPEAKING}} = 0.25 \text{bass} + (0.07 + 0.26 \text{mid}) \sin(5.0 n_x + 11.0 t) \cos(5.0 n_y - 9.0 t) + 0.44 \text{spread} \cdot \text{treble}$$
  - Multi-Band Acoustic Physics:
    - Bass: Radial core expansion and explosive shockwave punch ($0.25 \times \text{bass}$)
    - Mid: Fast transverse surface waves ($k=5.0$, wave speeds $11.0$ and $-9.0\text{ rad/s}$)
    - Treble: High-frequency corona spike dispersion ($0.44 \times \text{spread} \times \text{treble}$)
  - Speech Cadence Synthesizer Fallback (active when raw audio $< 0.03$):
    $$\text{syllable} = \left(\max(0, 0.65 \sin(7.2 t) + 0.35 \sin(11.7 t))\right)^{1.4}$$
    $$\text{cadence} = 0.45 + 0.55 \max(0, \sin(2.1 t + 0.5))$$
    $$\text{rawBass} = 0.22 + 0.65 \times \text{syllable} \times \text{cadence}$$
    $$\text{rawMid} = 0.18 + 0.58 \times |\sin(9.5 t)| \times \text{cadence}$$
    $$\text{rawTreble} = 0.14 + 0.52 \times |\cos(14.3 t)| \times \text{cadence}$$

---

### State 5: `WEB_SEARCH`
- **Key Binding**: `[5]`
- **Color Name**: Cyber Azure
- **Hex Code**: `#38bdf8`
- **RGB Normalized**: `(0.21961, 0.74118, 0.97255)` (8-bit: `56, 189, 248`)
- **Three.Color Representation**: `new THREE.Color('#38bdf8')`
- **Accent / Crest Color**: Intense white for radar beam sweep and hit pings
- **Core Glow Parameters**:
  - Scale: $2.45 + 0.25 \times w_{\text{WEB\_SEARCH}} = 2.70$
  - Opacity: $0.36$
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $1.15$
  - Ring 1 Opacity: $0.62 \times w_{\text{WEB\_SEARCH}}$
  - Ring 2 Opacity: $0.62 \times 0.78 \times w_{\text{WEB\_SEARCH}} \approx 0.4836$
  - Ring 3: **Active Planetary Radar Reference Ring**
    - Opacity: $0.45 \times w_{\text{WEB\_SEARCH}}$
    - Position: $(0, 0, 0)$
    - Rotation: $(\pi/2 + 0.18, 0, -0.38) = (1.7508, 0, -0.38)\text{ rad}$
    - Scale: $1.16$
- **3D Scene Orientation & Rotational Drift**:
  - Planetary Axial Tilt:
    $\Delta \text{rot}_y = dt \times 0.38$
    $\text{target\_rot}_x = 0.18\text{ rad} \approx 10.31^\circ$
    $\text{target\_rot}_z = -0.38\text{ rad} \approx -21.77^\circ$ (simulating Earth's $23.44^\circ$ obliquity)
- **Geometry Morph Target (Quantized Lat/Lon Globe)**:
  - 12 Longitudinal Meridians (for even indices $i \equiv 0 \pmod 2$):
    $$\theta_g = \text{round}\left(\frac{\theta}{2\pi / 12}\right) \times \left(\frac{2\pi}{12}\right)$$
  - 8 Latitudinal Parallels (for odd indices $i \equiv 1 \pmod 2$):
    $$\phi_g = \text{clamp}\left(\text{round}\left(\frac{\phi}{\pi / 8}\right) \times \left(\frac{\pi}{8}\right), 0.16, \pi - 0.16\right)$$
  - Projected Normal: $\vec{g} = (\sin\phi_g \cos\theta_g, \cos\phi_g, \sin\phi_g \sin\theta_g)$
  - Target Geometry Normal: $\vec{n}_{\text{globe}} = 0.18 \vec{n} + 0.82 \vec{g}$
  - Morph Lerp: $\vec{d} \mathrel{+}= (\vec{n}_{\text{globe}} - \vec{d}) \times w_{\text{WEB\_SEARCH}}$
- **Radar Beam & Hit Pings**:
  - Radar Meridian Sweep: $\theta_{\text{radar}} = ((2.4 t) \bmod 2\pi) - \pi$
  - Angular Distance: $\Delta \theta = |\theta - \theta_{\text{radar}}|$ (wrapped to $[0, \pi]$)
  - Gaussian Beam: $\text{beam} = \exp(-(\Delta \theta)^2 / 0.09)$
  - Hit Ping Detection: $\text{ping} = \mathbb{I}\left(\sin(19.0 \times \text{phase} + \lfloor 4.5 t \rfloor \times 3.7) > 0.965\right)$
  - Displacement: $\text{disp}_{\text{WEB\_SEARCH}} = 0.14 \times \text{beam} + 0.22 \times \text{ping}$
  - Extra Highlight: $+ w_{\text{WEB\_SEARCH}} \times \min(1.0, 0.9 \times \text{beam} + \text{ping})$

---

### State 6: `DEEP_RESEARCH`
- **Key Binding**: `[6]`
- **Color Name**: Periwinkle
- **Hex Code**: `#818cf8`
- **RGB Normalized**: `(0.50588, 0.54902, 0.97255)` (8-bit: `129, 140, 248`)
- **Three.Color Representation**: `new THREE.Color('#818cf8')`
- **Accent / Crest Color**: Deep violet-indigo with brilliant core particle sparks
- **Core Glow Parameters**:
  - Scale Modulation: $\text{scale} = 2.45 + w_{\text{DEEP\_RESEARCH}} \times (0.35 + 0.2 \sin(3.5 t)) = 2.80 + 0.2 \sin(3.5 t)$ (Range: $[2.60, 3.00]$)
  - Opacity: $0.36$
  - Pulse Frequency: $\omega = 3.5\text{ rad/s}$ ($f \approx 0.5570\text{ Hz}$, Period $T \approx 1.795\text{ s}$)
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $1.50$
  - Ring 1 Opacity: $0.55 \times w_{\text{DEEP\_RESEARCH}}$
  - Ring 2 Opacity: $0.55 \times 0.78 \times w_{\text{DEEP\_RESEARCH}} \approx 0.4290$
  - Ring 2 Scale: $1.0 + 0.08 \times w_{\text{DEEP\_RESEARCH}} = 1.08$
  - Ring 3: Inactive ($\text{opacity} = 0$)
- **3D Scene Orientation & Rotational Drift**:
  - Default axial drift ($\Delta \text{rot}_y = dt \times 0.15, \text{rot}_x = 0.08 \sin(0.4 t)$)
- **Geometry Morph Target (3 Nested Concentric Counter-Rotating Knowledge Shells)**:
  - Shell Assignment: $s = i \bmod 3$
  - **Shell 0 (Dense Knowledge Nucleus)**:
    - Scale: $0.52$
    - Spin Angular Velocity: $\omega_0 = +1.35\text{ rad/s}$ around Y
    - Highlight Boost: $+0.55 \times w_{\text{DEEP\_RESEARCH}}$
  - **Shell 1 (Tilted Gyro-Orbital Layer)**:
    - Scale: $0.88$
    - Spin Angular Velocity: $\omega_1 = -0.85\text{ rad/s}$ (counter-spin) around Y
    - Fixed Orbital Inclination: Rotated around X axis by $0.48\text{ rad} \approx 27.50^\circ$
    - Highlight Boost: $+0.15 \times w_{\text{DEEP\_RESEARCH}}$
  - **Shell 2 (Diffuse Outer Halo)**:
    - Scale: $1.20$
    - Spin Angular Velocity: $\omega_2 = +0.42\text{ rad/s}$ around Y
    - Highlight Boost: $+0.15 \times w_{\text{DEEP\_RESEARCH}}$
  - Mathematical Transformation:
    $$s_x = (n_x \cos(\text{spin}) - n_z \sin(\text{spin})) \times \text{scale}_s$$
    $$s_y = n_y \times \text{scale}_s$$
    $$s_z = (n_x \sin(\text{spin}) + n_z \cos(\text{spin})) \times \text{scale}_s$$
    If $s = 1$:
    $$s_y' = s_y \cos(0.48) - s_z \sin(0.48), \quad s_z' = s_y \sin(0.48) + s_z \cos(0.48)$$
  - Morph Lerp: $\vec{d} \mathrel{+}= (\vec{s} - \vec{d}) \times w_{\text{DEEP\_RESEARCH}}$
- **Particle Dynamics & Turbulence**:
  - Orbital Shimmer: $\text{disp}_{\text{DEEP\_RESEARCH}} = 0.035 \sin(3.0 \times \text{phase} + 4.2 t)$

---

### State 7: `CODING`
- **Key Binding**: `[7]`
- **Color Name**: Matrix Mint
- **Hex Code**: `#4ade80`
- **RGB Normalized**: `(0.29020, 0.87059, 0.50196)` (8-bit: `74, 222, 128`)
- **Three.Color Representation**: `new THREE.Color('#4ade80')`
- **Accent / Crest Color**: Pure electric green/white digital cascade pulses
- **Core Glow Parameters**:
  - Scale: $2.45$
  - Opacity: $0.36$
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $0.70$
  - Ring 1 Opacity: $0.48 \times w_{\text{CODING}}$
  - Ring 2 Opacity: $0.48 \times 0.78 \times w_{\text{CODING}} = 0.3744$
  - Ring 3: Inactive ($\text{opacity} = 0$)
- **3D Scene Orientation & Rotational Drift**:
  - Isometric Cubical Alignment:
    $\Delta \text{rot}_y = dt \times 0.34$
    $\text{target\_rot}_x = 0.42\text{ rad} \approx 24.06^\circ$
    $\text{target\_rot}_z = 0.18\text{ rad} \approx 10.31^\circ$
- **Geometry Morph Target (Beveled 3D Holo-Cube)**:
  - Chebyshev / $L_\infty$ Distance Normalization:
    $$m = \max(|n_x|, |n_y|, |n_z|) \lor 1$$
    $$\vec{c} = \left(\frac{n_x}{m} \times 0.77, \frac{n_y}{m} \times 0.77, \frac{n_z}{m} \times 0.77\right)$$
  - Bevel Blending (16% spherical curvature, 84% cube face alignment):
    $$\vec{n}_{\text{cube}} = 0.16 \vec{n} + 0.84 \vec{c}$$
  - Morph Lerp: $\vec{d} \mathrel{+}= (\vec{n}_{\text{cube}} - \vec{d}) \times w_{\text{CODING}}$
  - Digital Code Rain Column Seeds:
    $$q_x = \text{round}(c_x \times 5) + 10, \quad q_z = \text{round}(c_z \times 5) + 10$$
    $$\text{seed}_i = ((q_x \times 37 + q_z \times 17) \bmod 19) \times 0.55$$
- **Cascading Digital Code Stream Physics**:
  - Downward Rain Flow:
    $$\text{stream} = ((1 - n_y) \times 1.8 + 1.55 t + \text{seed}_i) \bmod 1.0$$
  - Falling Leading-Edge Droplet Pulse:
    $$\text{head} = \exp\left(-((stream - 0.12) \times 9.0)^2\right)$$
  - Particle Displacement: $\text{disp}_{\text{CODING}} = 0.07 \times \text{head}$
  - Code Luminescence Boost: $+ 0.95 \times \text{head} \times w_{\text{CODING}}$

---

### State 8: `VISION_SCAN`
- **Key Binding**: `[8]`
- **Color Name**: Laser Rose
- **Hex Code**: `#f472b6`
- **RGB Normalized**: `(0.95686, 0.44706, 0.71373)` (8-bit: `244, 114, 182`)
- **Three.Color Representation**: `new THREE.Color('#f472b6')`
- **Accent / Crest Color**: Pure white laser slice illumination
- **Core Glow Parameters**:
  - Scale: $2.45$
  - Opacity: $0.36$
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $0.40$
  - Ring 1 Opacity: $0.38 \times w_{\text{VISION\_SCAN}}$
  - Ring 2 Opacity: $0.38 \times 0.78 \times w_{\text{VISION\_SCAN}} \approx 0.2964$
  - Ring 3: **Active Lidar Slicing Ring**
    - Opacity: $0.82 \times w_{\text{VISION\_SCAN}}$
    - Sweep Elevation: $y_{\text{scan}} = \sin(2.1 t) \times 0.94$ (Range: $[-0.94, +0.94]$, Period $T \approx 2.99\text{ s}$)
    - Cross-Sectional Slice Radius: $r_{\text{slice}} = \sqrt{\max(0.06, 1 - y_{\text{scan}}^2)}$
    - Ring 3 Position: $(0, y_{\text{scan}} \times \text{BASE\_RADIUS}, 0)$
    - Ring 3 Rotation: $(\pi/2, 0, 0)$
    - Ring 3 Scale: $r_{\text{slice}} \times 1.05$
- **3D Scene Orientation & Rotational Drift**:
  - $\Delta \text{rot}_y = dt \times 0.18$
  - $\text{target\_rot}_x = 0.08\text{ rad}$
  - $\text{target\_rot}_z = 0.00\text{ rad}$
- **Geometry & Particle Displacement**:
  - Geometry Base: Fibonacci Sphere ($\vec{d} = \vec{n}$)
  - Planar Distance: $\Delta y = n_y - y_{\text{scan}}$
  - Optical Laser Band Excitation:
    $$\text{band} = \exp\left(-\frac{\Delta y^2}{0.0075}\right)$$
    (Slice thickness standard deviation $\sigma = \sqrt{0.0075 / 2} \approx 0.0612$, producing a knife-edge laser line).
  - Displacement Formula:
    $$\text{disp}_{\text{VISION\_SCAN}} = 0.22 \times \text{band} - 0.03$$
  - Laser Illumination Crest: $+ 1.1 \times \text{band} \times w_{\text{VISION\_SCAN}}$

---

### State 9: `MEMORY_SYNC`
- **Key Binding**: `[9]`
- **Color Name**: Teal-Cyan
- **Hex Code**: `#2dd4bf`
- **RGB Normalized**: `(0.17647, 0.83137, 0.74902)` (8-bit: `45, 212, 191`)
- **Three.Color Representation**: `new THREE.Color('#2dd4bf')`
- **Accent / Crest Color**: Intense cyan-white flux in the central toroidal throat
- **Core Glow Parameters**:
  - Central Void Chamber Contraction:
    $$\text{scale} = 2.45 - 0.55 \times w_{\text{MEMORY\_SYNC}} = 1.90$$
    $$\text{opacity} = 0.36 - 0.12 \times w_{\text{MEMORY\_SYNC}} = 0.24$$
    (Volumetric core shrinks and dims, opening a hollow black hole/tunnel through the core).
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $1.30$
  - Ring 1 Opacity: $0.52 \times w_{\text{MEMORY\_SYNC}}$
  - Ring 2 Opacity: $0.52 \times 0.78 \times w_{\text{MEMORY\_SYNC}} = 0.4056$
  - Ring 3: Inactive ($\text{opacity} = 0$)
- **3D Scene Orientation & Rotational Drift**:
  - Polar Vortex View Inclination:
    $\Delta \text{rot}_y = dt \times 0.32$
    $\text{target\_rot}_x = 0.58\text{ rad} \approx 33.23^\circ$ (tilted forward to expose the open polar tunnel)
    $\text{target\_rot}_z = 0.12 \sin(0.6 t)$
- **Geometry Morph Target (Arc-Reactor 3D Torus & Poloidal Flow)**:
  - Poloidal Angle Evolution:
    $$\theta_{\text{poloidal}}(t) = 2.0 \phi - 2.6 t$$
  - Torus Cross-Sectional Distance:
    $$r_{\text{torus}} = 0.78 + 0.34 \cos(\theta_{\text{poloidal}})$$
    (Major torus radius $R_0 = 0.78$, minor tube radius $r_0 = 0.34$, inner throat clearance $0.44$, outer rim $1.12$).
  - 3D Coordinates:
    $$t_x = r_{\text{torus}} \cos\theta$$
    $$t_y = 0.38 \sin(\theta_{\text{poloidal}})$$
    $$t_z = r_{\text{torus}} \sin\theta$$
  - Morph Lerp: $\vec{d} \mathrel{+}= (\vec{t} - \vec{d}) \times w_{\text{MEMORY\_SYNC}}$
  - Throat Flux Illumination:
    $$\text{extraHighlight} \mathrel{+}= w_{\text{MEMORY\_SYNC}} \times \max(0, -0.65 \cos(\theta_{\text{poloidal}}))$$

---

### State 10: `EXECUTING_TOOL`
- **Key Binding**: `[0]`
- **Color Name**: Neon Violet
- **Hex Code**: `#c084fc`
- **RGB Normalized**: `(0.75294, 0.51765, 0.98824)` (8-bit: `192, 132, 252`)
- **Three.Color Representation**: `new THREE.Color('#c084fc')`
- **Accent / Crest Color**: Electric ultraviolet facet highlights
- **Core Glow Parameters**:
  - Scale: $2.45$
  - Opacity: $0.36$
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $2.80$ (highest rotational velocity in the entire visualizer)
  - Ring 1 Opacity: $0.65 \times w_{\text{EXECUTING\_TOOL}}$
  - Ring 2 Opacity: $0.65 \times 0.78 \times w_{\text{EXECUTING\_TOOL}} \approx 0.5070$
  - Ring 3: Inactive ($\text{opacity} = 0$)
- **3D Scene Orientation & Rotational Drift**:
  - High-Speed Multi-Axis Spin:
    $\Delta \text{rot}_y = dt \times 0.95$
    $\Delta \text{rot}_z = dt \times 0.45$
- **Geometry & Particle Displacement**:
  - Geometry Base: Fibonacci Sphere ($\vec{d} = \vec{n}$)
  - Octupole 3D Standing Facets & Jitter:
    $$\text{disp}_{\text{TOOL}} = 0.16 \sin(7.0 n_x + 4.0 t) \sin(7.0 n_y - 4.0 t) \sin(7.0 n_z) + 0.05 \sin(8.0 t)$$
    (Spatial standing wave frequency $k=7.0\text{ rad/unit}$, phase velocity $v=4.0\text{ rad/s}$, high-frequency tool shudder at $8.0\text{ rad/s}$).

---

### State 11: `ALERT`
- **Key Binding**: `[-]`
- **Color Name**: Crimson-Coral
- **Hex Code**: `#fb7185`
- **RGB Normalized**: `(0.98431, 0.44314, 0.52157)` (8-bit: `251, 113, 133`)
- **Three.Color Representation**: `new THREE.Color('#fb7185')`
- **Accent / Crest Color**: Blinding white-hot shockwave corona ($+0.55 \times \text{beat} \times w_{\text{ALERT}}$)
- **Twin-Beat Cardiac Shockwave (Lub-Dub Engine)**:
  - Normalized Heartbeat Cycle: $\tau = (1.18 t) \bmod 1.0$ (Heart rate $f = 1.18\text{ Hz} \approx 70.8\text{ BPM}$)
  - Systolic Pulse ("Lub"): $\text{pulse}_1 = \exp\left(-((\tau - 0.12) \times 14.0)^2\right)$
  - Diastolic Pulse ("Dub"): $\text{pulse}_2 = 0.68 \exp\left(-((\tau - 0.30) \times 16.0)^2\right)$
  - Total Cardiac Beat Amplitude:
    $$\text{alertBeat}(\tau) = \exp\left(-((\tau - 0.12) \times 14.0)^2\right) + 0.68 \exp\left(-((\tau - 0.30) \times 16.0)^2\right)$$
- **Core Glow Parameters**:
  - Scale Modulation: $\text{scale} = 2.45 + w_{\text{ALERT}} \times 0.95 \times \text{alertBeat}$ (Peaks at $3.40$ during systole)
  - Opacity Modulation: $\text{opacity} = 0.36 + w_{\text{ALERT}} \times 0.35 \times \text{alertBeat}$ (Peaks at $0.71$ during systole)
- **Gyroscopic & Scanner Rings**:
  - Global Speed Multiplier: $2.20$
  - Ring 1 Opacity: $(0.45 + 0.45 \times \text{alertBeat}) \times w_{\text{ALERT}}$ (Pulses between $0.45$ and $0.90$)
  - Ring 2 Opacity: Ring 1 Opacity $\times 0.78$ (Pulses between $0.3510$ and $0.7020$)
  - Ring 1 Scale: $1.0 + w_{\text{ALERT}} \times 0.12 \times \text{alertBeat}$
  - Ring 3: Inactive ($\text{opacity} = 0$)
- **3D Scene Orientation & Rotational Drift**:
  - Rapid Alarm Vibration & Spin:
    $\Delta \text{rot}_y = dt \times 0.55$
    $\text{target\_rot}_x = 0.06 \sin(9.0 t)$ (Alarm shudder frequency $\omega = 9.0\text{ rad/s}$)
- **Geometry & Particle Displacement**:
  - Geometry Base: Fibonacci Sphere ($\vec{d} = \vec{n}$)
  - Radial Shockwave Spikes:
    $$\text{disp}_{\text{ALERT}} = \text{alertBeat} \times \left(0.18 + 0.26 \times \text{spread} + 0.12 \sin(9.0 n_x) \cos(9.0 n_y)\right)$$
  - Crest Luminescence Flash: $+ 0.55 \times \text{alertBeat} \times w_{\text{ALERT}}$

---

## 3. State Parameters Comprehensive Reference Matrix

| State Name | Key | Hex Code | Base Radius | Core Scale Range | Core Opacity | Ring Speed | Ring 1 Opacity | Ring 3 Mode | Primary Morph Formula |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `IDLE` | `1` | `#67e8f9` | 1.72 | $2.30 - 2.60$ | 0.36 | 0.25 | 0.22 | Off | Dual surface sinusoidal wave |
| `LISTENING` | `2` | `#00f0ff` | 1.72 | $2.70 - 3.40$ | 0.36 | 0.60 | 0.50 | Off | $-0.07$ contraction + sonar ripples + mic |
| `THINKING` | `3` | `#fbbf24` | 1.72 | $2.52 - 3.08$ | 0.50 | 2.40 | 0.65 | Off | Hemisphere twist vortex + 3D harmonics |
| `SPEAKING` | `4` | `#e0f2fe` | 1.72 | $2.90 - 4.05$ | $0.56 - 0.84$ | 0.90 | 0.55 | Off | Bass punch + mid waves + treble corona |
| `WEB_SEARCH` | `5` | `#38bdf8` | 1.72 | 2.70 | 0.36 | 1.15 | 0.62 | Radar Ref | Lat/Lon quantized globe + radar sweep |
| `DEEP_RESEARCH` | `6` | `#818cf8` | 1.72 | $2.60 - 3.00$ | 0.36 | 1.50 | 0.55 | Off | 3 nested concentric counter-spinning shells |
| `CODING` | `7` | `#4ade80` | 1.72 | 2.45 | 0.36 | 0.70 | 0.48 | Off | Beveled cube + falling code rain |
| `VISION_SCAN` | `8` | `#f472b6` | 1.72 | 2.45 | 0.36 | 0.40 | 0.38 | Lidar Slice | Sweeping lidar slice ring + laser plane |
| `MEMORY_SYNC` | `9` | `#2dd4bf` | 1.72 | 1.90 | 0.24 | 1.30 | 0.52 | Off | Arc-Reactor 3D torus + poloidal flow |
| `EXECUTING_TOOL`| `0` | `#c084fc` | 1.72 | 2.45 | 0.36 | 2.80 | 0.65 | Off | Fast multi-axis spin + octupole facets |
| `ALERT` | `-` | `#fb7185` | 1.72 | $2.45 - 3.40$ | $0.36 - 0.71$ | 2.20 | $0.45 - 0.90$ | Off | Twin-beat cardiac shockwave + spikes |

---

## 4. Physics Engine & Turbulence Equations

### 4.1 Fibonacci Golden Spiral Sphere Sampling
Uniform spherical sampling of $N$ particles without polar clustering:
$$\text{goldenAngle} = \pi (3 - \sqrt{5}) \approx 2.399963229728653\text{ rad}$$
For each particle $i \in [0, N-1]$:
$$y_i = 1 - \left(\frac{i}{N - 1}\right) \times 2$$
$$r_i = \sqrt{\max(0, 1 - y_i^2)}$$
$$\theta_i = \text{goldenAngle} \times i$$
$$n_x = \cos(\theta_i) r_i + \delta_x, \quad n_y = y_i + \delta_y, \quad n_z = \sin(\theta_i) r_i + \delta_z$$
where $\delta \sim \mathcal{U}(-0.0125, +0.0125)$ introduces subtle micro-jitter, preventing visible moiré patterns. Normalizing:
$$\vec{n} = \frac{(n_x, n_y, n_z)}{\|(n_x, n_y, n_z)\|}$$
Base position: $\vec{P}_{\text{base}} = \vec{n} \times R_{\text{BASE}}$ where $R_{\text{BASE}} = 1.72$.

### 4.2 Lat/Lon Globe Target Morph (`WEB_SEARCH`)
Partitions particles into 12 meridians and 8 parallels:
- Spherical coordinates: $\theta = \text{atan2}(n_z, n_x)$, $\phi = \arccos(\text{clamp}(n_y, -1, 1))$.
- Even $i$: $\theta_g = \text{round}\left(\frac{\theta}{2\pi / 12}\right) \times \left(\frac{2\pi}{12}\right)$
- Odd $i$: $\phi_g = \text{clamp}\left(\text{round}\left(\frac{\phi}{\pi / 8}\right) \times \left(\frac{\pi}{8}\right), 0.16, \pi - 0.16\right)$
- Project back to sphere: $\vec{g} = (\sin\phi_g \cos\theta_g, \cos\phi_g, \sin\phi_g \sin\theta_g)$
- Target: $\vec{n}_{\text{globe}} = 0.18 \vec{n} + 0.82 \vec{g}$.

### 4.3 Beveled Holo-Cube Target Morph (`CODING`)
Projects spherical coordinates onto cube faces using $L_\infty$ norm:
$$m = \max(|n_x|, |n_y|, |n_z|) \lor 1$$
$$\vec{c} = \frac{\vec{n}}{m} \times 0.77$$
$$\vec{n}_{\text{cube}} = 0.16 \vec{n} + 0.84 \vec{c}$$

### 4.4 Arc-Reactor Torus & Poloidal Flow (`MEMORY_SYNC`)
Continuous closed toroidal circulation:
$$\theta_{\text{poloidal}}(t) = 2.0 \phi - 2.6 t$$
$$r_{\text{torus}} = 0.78 + 0.34 \cos(\theta_{\text{poloidal}})$$
$$\vec{t} = (r_{\text{torus}} \cos\theta, 0.38 \sin(\theta_{\text{poloidal}}), r_{\text{torus}} \sin\theta)$$

### 4.5 Particle Twinkle & Crest Radiance
Particle color luminance is computed per frame:
$$\text{crest} = \min\left(1, \max\left(0, \text{displacement} \times 2.6 + \text{extraHighlight} + w_{\text{SPEAKING}} \cdot \text{bass} \cdot 0.45 + w_{\text{ALERT}} \cdot \text{alertBeat} \cdot 0.55 + 0.14\right)\right)$$
$$\text{twinkle} = 0.85 + 0.15 \sin(2.6 t + \text{phase}_i)$$
$$\vec{C}_i = \left(\vec{C}_{\text{blended}} + (1 - \vec{C}_{\text{blended}}) \times \text{crest}\right) \times \text{twinkle}$$

---

## 5. Exponential Damping Engine & State Interpolation Pipeline

### 5.1 Mathematical Derivation
Transitions between discrete states must never jump abruptly or overshoot. The visualizer employs first-order exponential smoothing:
$$\frac{dw_k}{dt} = -k (w_k - w_k^*)$$
where $w_k^*$ is $1$ if $k = \text{activeState}$ and $0$ otherwise.
Integrating over timestep $\Delta t$:
$$w_k(t + \Delta t) = w_k(t) + \left(w_k^* - w_k(t)\right) \left(1 - e^{-k \Delta t}\right)$$

### 5.2 Damping Constants & Temporal Metrics
1. **State Weight & Color Damping ($k = 6.2\text{ s}^{-1}$)**:
   - Discrete damping factor: `damp = 1 - Math.exp(-6.2 * dt)`
   - Half-Life ($t_{1/2}$): $\frac{\ln 2}{6.2} \approx 0.1118\text{ s} \approx 112\text{ ms}$
   - 90% Settling Time: $\frac{\ln 10}{6.2} \approx 0.3714\text{ s} \approx 371\text{ ms}$
   - 95% Settling Time: $\frac{\ln 20}{6.2} \approx 0.4832\text{ s} \approx 483\text{ ms}$
   - 99% Settling Time: $\frac{\ln 100}{6.2} \approx 0.7428\text{ s} \approx 743\text{ ms}$
2. **Audio Band Spectrum Damping ($k = 14.0\text{ s}^{-1}$)**:
   - Discrete damping factor: `audioDamp = 1 - Math.exp(-14 * dt)`
   - Half-Life ($t_{1/2}$): $\frac{\ln 2}{14.0} \approx 0.0495\text{ s} \approx 49.5\text{ ms}$ (~3 frames at 60 FPS)
   - Settles rapidly to capture punchy transients while filtering out high-frequency noise.
3. **Safety Timestep Clamping**:
   - $\Delta t = \min(0.05, \text{delta})$
   - If the user switches desktop windows or the browser throttles background animations, $\Delta t$ is capped at $50\text{ ms}$, completely eliminating numerical overflow or geometry tearing.

### 5.3 Unified Interpolation Pipeline
At each render tick:
```
1. dt = Math.min(0.05, clock.getDelta())
2. damp = 1 - Math.exp(-6.2 * dt)
3. For each state k:
     w[k] += ((activeState === k ? 1 : 0) - w[k]) * damp
4. blendedColor.lerp(palette[activeState], damp)
5. mesh.rotation.x += (targetRotX - mesh.rotation.x) * damp
   mesh.rotation.z += (targetRotZ - mesh.rotation.z) * damp
6. rings[1..2].rotation += dt * ringSpeed(w)
```

---

## 6. Cardiac Shockwave Mechanics & State Transition Pulses

### 6.1 Lub-Dub Cardiac Cycle Formulation
The ALERT state models human cardiac electrophysiology with two distinct contraction phases:
$$\tau = (1.18 t) \bmod 1.0$$
$$\text{Pulse 1 (Systole / Lub)}: \quad P_1(\tau) = \exp\left(-((\tau - 0.12) \times 14.0)^2\right)$$
$$\text{Pulse 2 (Diastole / Dub)}: \quad P_2(\tau) = 0.68 \exp\left(-((\tau - 0.30) \times 16.0)^2\right)$$
$$\text{alertBeat}(\tau) = P_1(\tau) + P_2(\tau)$$

Key Physiological Properties:
- Period: $T = \frac{1}{1.18} \approx 0.847\text{ s} \implies 70.8\text{ BPM}$.
- Primary contraction occurs at $12\%$ of the cycle ($\tau = 0.12, t \approx 102\text{ ms}$ into cycle).
- Secondary contraction occurs at $30\%$ of the cycle ($\tau = 0.30, t \approx 254\text{ ms}$ into cycle).
- Quiescent recovery phase occupies remaining $70\%$ of the cycle ($0.38 \le \tau < 1.0$), ensuring high dynamic contrast.

### 6.2 State Transition Cardiac Shockwave Pulse
When transitioning between any states (e.g. from `IDLE` to `LISTENING` or `THINKING` to `ALERT`), the transition engine triggers a one-shot cardiac shockwave pulse:
1. **Trigger Condition**: Detected when `currentActiveState !== previousActiveState`.
2. **Transition Timer**: `shockwaveAge = 0`, active duration $T_{\text{pulse}} = 0.45\text{ s}$ ($450\text{ ms}$).
3. **Radial Expansion**:
   $$r_{\text{shock}}(t) = R_{\text{BASE}} \times \left(1.0 + 0.35 \times \frac{t - t_0}{T_{\text{pulse}}}\right)$$
4. **Opacity Falloff & Decay Rate**:
   $$\alpha_{\text{shock}}(t) = \alpha_0 \times \left(1 - \frac{t - t_0}{T_{\text{pulse}}}\right)^2$$
   decaying quadratically from $\alpha_0 = 0.65$ to $0$ over $450\text{ ms}$.

---

## 7. TypeScript Structures & Architecture Blueprint

Below are the exact TypeScript definitions designed for `src/components/dashboard/holographic-core/`:

```typescript
// src/components/dashboard/holographic-core/types.ts

import * as THREE from 'three';

export type JarvisVisualState =
  | 'IDLE'
  | 'LISTENING'
  | 'THINKING'
  | 'SPEAKING'
  | 'WEB_SEARCH'
  | 'DEEP_RESEARCH'
  | 'CODING'
  | 'VISION_SCAN'
  | 'MEMORY_SYNC'
  | 'EXECUTING_TOOL'
  | 'ALERT';

export interface StateMetadata {
  key: string;
  id: JarvisVisualState;
  colorName: string;
  hex: string;
  rgb: [number, number, number];
  normalizedRgb: [number, number, number];
  desc: string;
}

export interface StateWeights {
  IDLE: number;
  LISTENING: number;
  THINKING: number;
  SPEAKING: number;
  WEB_SEARCH: number;
  DEEP_RESEARCH: number;
  CODING: number;
  VISION_SCAN: number;
  MEMORY_SYNC: number;
  EXECUTING_TOOL: number;
  ALERT: number;
}

export interface AudioBands {
  bass: number;
  mid: number;
  treble: number;
}

export interface HolographicCoreProps {
  count?: number;
  activeState?: JarvisVisualState;
  audioLevel?: number;
  className?: string;
}

export interface ParticleBuffers {
  positions: Float32Array;
  colors: Float32Array;
  normals: Float32Array;
  globeNormals: Float32Array;
  cubeNormals: Float32Array;
  thetas: Float32Array;
  phis: Float32Array;
  phases: Float32Array;
  spreads: Float32Array;
  colSeeds: Float32Array;
}
```

```typescript
// src/components/dashboard/holographic-core/constants.ts

import { JarvisVisualState, StateMetadata } from './types';

export const BASE_RADIUS = 1.72;

export const JARVIS_STATES: StateMetadata[] = [
  {
    key: '1',
    id: 'IDLE',
    colorName: 'Ice-Cyan',
    hex: '#67e8f9',
    rgb: [103, 232, 249],
    normalizedRgb: [0.40392, 0.90980, 0.97647],
    desc: 'Calm breathing surface wave, slow axial drift, soft dual rings'
  },
  {
    key: '2',
    id: 'LISTENING',
    colorName: 'Sky-Cyan',
    hex: '#00f0ff',
    rgb: [0, 240, 255],
    normalizedRgb: [0.00000, 0.94118, 1.00000],
    desc: 'Inward focus contraction + concentric equatorial-to-polar sonar ripples + live mic reactivity'
  },
  {
    key: '3',
    id: 'THINKING',
    colorName: 'Amber-Gold',
    hex: '#fbbf24',
    rgb: [251, 191, 36],
    normalizedRgb: [0.98431, 0.74902, 0.14118],
    desc: 'Counter-twisting hemisphere vortex + 3D spherical-harmonic lobes + fast gyroscope rings'
  },
  {
    key: '4',
    id: 'SPEAKING',
    colorName: 'White-Ice',
    hex: '#e0f2fe',
    rgb: [224, 242, 254],
    normalizedRgb: [0.87843, 0.94902, 0.99608],
    desc: 'Multi-band audio reactivity (bass core punch, mid standing waves, treble corona spikes)'
  },
  {
    key: '5',
    id: 'WEB_SEARCH',
    colorName: 'Cyber Azure',
    hex: '#38bdf8',
    rgb: [56, 189, 248],
    normalizedRgb: [0.21961, 0.74118, 0.97255],
    desc: '3D planetary lat/lon wireframe globe on a 23.5° axial tilt with a sweeping meridian radar beam and live search-hit data pings'
  },
  {
    key: '6',
    id: 'DEEP_RESEARCH',
    colorName: 'Periwinkle',
    hex: '#818cf8',
    rgb: [129, 140, 248],
    normalizedRgb: [0.50588, 0.54902, 0.97255],
    desc: 'Sphere splits into 3 nested counter-rotating concentric knowledge shells (core, tilted mid-shell, outer halo)'
  },
  {
    key: '7',
    id: 'CODING',
    colorName: 'Matrix Mint',
    hex: '#4ade80',
    rgb: [74, 222, 128],
    normalizedRgb: [0.29020, 0.87059, 0.50196],
    desc: 'Morphs into a beveled 3D holo-cube with cascading vertical digital code streams down its faces'
  },
  {
    key: '8',
    id: 'VISION_SCAN',
    colorName: 'Laser Rose',
    hex: '#f472b6',
    rgb: [244, 114, 182],
    normalizedRgb: [0.95686, 0.44706, 0.71373],
    desc: 'Precision horizontal optical lidar ring & laser plane sweeping smoothly from top pole to bottom pole'
  },
  {
    key: '9',
    id: 'MEMORY_SYNC',
    colorName: 'Teal-Cyan',
    hex: '#2dd4bf',
    rgb: [45, 212, 191],
    normalizedRgb: [0.17647, 0.83137, 0.74902],
    desc: 'Opens a central polar tunnel into an Arc-Reactor 3D torus with continuous poloidal particle flow'
  },
  {
    key: '0',
    id: 'EXECUTING_TOOL',
    colorName: 'Neon Violet',
    hex: '#c084fc',
    rgb: [192, 132, 252],
    normalizedRgb: [0.75294, 0.51765, 0.98824],
    desc: 'High-speed multi-axis spin with crisp octupole geometric facets'
  },
  {
    key: '-',
    id: 'ALERT',
    colorName: 'Crimson-Coral',
    hex: '#fb7185',
    rgb: [251, 113, 133],
    normalizedRgb: [0.98431, 0.44314, 0.52157],
    desc: 'Urgent twin-beat cardiac shockwave (lub-dub) with sharp radial warning spikes'
  }
];

export const STATE_COLORS: Record<JarvisVisualState, string> = Object.fromEntries(
  JARVIS_STATES.map((s) => [s.id, s.hex])
) as Record<JarvisVisualState, string>;

export const STATE_KEYS: JarvisVisualState[] = JARVIS_STATES.map((s) => s.id);
```

```typescript
// src/components/dashboard/holographic-core/state-machine.ts

import * as THREE from 'three';
import { JarvisVisualState, StateWeights } from './types';
import { STATE_KEYS, STATE_COLORS } from './constants';

export class StateTransitionEngine {
  private weights: StateWeights;
  private activeState: JarvisVisualState = 'IDLE';
  private blendedColor: THREE.Color;
  private palette: Record<JarvisVisualState, THREE.Color>;

  constructor(initialState: JarvisVisualState = 'IDLE') {
    this.activeState = initialState;
    this.weights = {
      IDLE: initialState === 'IDLE' ? 1 : 0,
      LISTENING: initialState === 'LISTENING' ? 1 : 0,
      THINKING: initialState === 'THINKING' ? 1 : 0,
      SPEAKING: initialState === 'SPEAKING' ? 1 : 0,
      WEB_SEARCH: initialState === 'WEB_SEARCH' ? 1 : 0,
      DEEP_RESEARCH: initialState === 'DEEP_RESEARCH' ? 1 : 0,
      CODING: initialState === 'CODING' ? 1 : 0,
      VISION_SCAN: initialState === 'VISION_SCAN' ? 1 : 0,
      MEMORY_SYNC: initialState === 'MEMORY_SYNC' ? 1 : 0,
      EXECUTING_TOOL: initialState === 'EXECUTING_TOOL' ? 1 : 0,
      ALERT: initialState === 'ALERT' ? 1 : 0,
    };

    this.palette = {} as Record<JarvisVisualState, THREE.Color>;
    for (const key of STATE_KEYS) {
      this.palette[key] = new THREE.Color(STATE_COLORS[key]);
    }
    this.blendedColor = new THREE.Color(STATE_COLORS[initialState]);
  }

  public setState(nextState: JarvisVisualState): void {
    if (this.activeState !== nextState) {
      this.activeState = nextState;
    }
  }

  public update(delta: number): {
    weights: StateWeights;
    blendedColor: THREE.Color;
    damp: number;
  } {
    const dt = Math.min(0.05, delta);
    const damp = 1 - Math.exp(-6.2 * dt);

    for (const key of STATE_KEYS) {
      const target = this.activeState === key ? 1 : 0;
      this.weights[key] += (target - this.weights[key]) * damp;
    }

    this.blendedColor.lerp(this.palette[this.activeState], damp);

    return {
      weights: this.weights,
      blendedColor: this.blendedColor,
      damp,
    };
  }
}
```

---

## 8. Conclusion

The authoritative visualizer HTML contains an elegant, mathematically sound, frame-rate independent engine. The extracted formulas and parameters provide an exact blueprint for the implementation phase in Milestone 1.2, ensuring flawless visual and functional fidelity with zero ambiguity.
