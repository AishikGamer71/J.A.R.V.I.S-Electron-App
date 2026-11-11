# J.A.R.V.I.S. 11-State 3D Holographic Core Visualizer Specification

**Document Version**: 1.0.0  
**Source Specification**: `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`  
**Target Environment**: J.A.R.V.I.S Electron App (`e:\Projects\J.A.R.V.I.S Electron App`)  
**Target Component**: `src/components/dashboard/sphere.tsx`  
**Author**: Teamwork Specification Miner (`spec_miner_survey_1`)  
**Date**: November 11, 2026  

---

## 1. Executive Summary

This specification provides the comprehensive reverse-engineered architecture, mathematical formulations, rendering pipeline, state transition logic, audio reactivity pipelines, and integration blueprint for the **3D Holographic Core Visualizer** extracted from `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`.

The visualizer replaces the legacy 4-state / gold-tinted particle sphere currently rendered in `src/components/dashboard/sphere.tsx` with an advanced, high-performance, 11-state multi-layer holographic core visualizer. The system features multi-layer depth compositing (dark contrast backdrop halo, volumetric glow sprite, dual gyroscopic rings, dynamic scanner ring, and a morphing 3D Fibonacci particle cloud), exponential weight-damped morphing between 11 discrete cognitive states, 3-band FFT audio reactivity, and seamless integration with the J.A.R.V.I.S. Electron application events.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | States | 11 Core Holographic States | 11 visual states representing distinct cognitive/operational states | State ID (`IDLE`, `LISTENING`, etc.) | Color, geometry, ring rotation, particle displacement | Defaults to `IDLE` on invalid state string | lines 268-364, 580-587 |
| 2 | Rendering | Multi-Layer Compositing | 4 distinct render-ordered layers (backdrop, core glow, rings, particles) | Scene graph hierarchy | Depth-sorted additive blended WebGL scene | Disables depth write to prevent z-fighting | lines 968-1048, 1320-1517 |
| 3 | Geometry | Fibonacci Sphere Sampling | Golden-spiral particle distribution with uniform spherical coverage | Particle count `N` (1800, 2600, 3800) | Normals, theta, phi, phase, spread buffers | Clamps radius to avoid NaN | lines 496-530, 1406-1440 |
| 4 | Geometry | Lat/Lon Globe Morph Target | Quantized meridian/parallel sphere target for `WEB_SEARCH` | Base coordinates | Quantized `globeNormals` Float32Array | Clamps polar singularities | lines 531-550, 1441-1460 |
| 5 | Geometry | Beveled Holo-Cube Target | Normalized cube projection target for `CODING` matrix stream | Base coordinates | Beveled `cubeNormals` Float32Array | Normalizes max axis to avoid division by 0 | lines 551-563, 1461-1473 |
| 6 | Physics | Toroidal Poloidal Flow | Arc-Reactor 3D torus transformation for `MEMORY_SYNC` | Phi, Theta, elapsed time `t` | Toroidal particle positions and polar tunnel | Continuous modulo wrapping | lines 877-887, 1823-1834 |
| 7 | Physics | 3-Shell Concentric Splitting | Counter-rotating knowledge shells for `DEEP_RESEARCH` | Particle index modulo 3, time `t` | Radial shell scales (0.52, 0.88, 1.20) | Safe axis rotation matrix | lines 842-863, 1788-1810 |
| 8 | Physics | Optical Lidar Scan Plane | Precision sweeping laser plane and slice ring for `VISION_SCAN` | Sine wave sweep `sin(t*2.1)*0.94` | Ring 3 elevation, slice radius, gaussian band | Square root clamped to >= 0.06 | lines 780-784, 914-919 |
| 9 | Physics | Cardiac Shockwave (Lub-Dub) | Dual-pulse exponential heartbeat for `ALERT` state | Periodic timer `(t*1.18)%1` | Radial shockwave and jitter displacement | Exponent decay clamped | lines 701-705, 925-928 |
| 10| Animation | Damped State Weight Morphing | Exponential decay lerping of 11 state weights concurrently | Frame delta `dt`, target active state | Continuous weights `w[state] in [0, 1]` | Clamps `dt` to 50ms maximum | lines 608-617, 1545-1554 |
| 11| Audio | Multi-Band Spectrum Analysis | 3-band FFT bin aggregation (Bass, Mid, Treble) | Web Audio `AnalyserNode` Uint8Array (128) | Normalized `[0, 1]` band floats | Silently catches AudioContext errors | lines 620-636, 1557-1573 |
| 12| Audio | Synthetic Cadence Synthesizer | Harmonic speech cadence simulation fallback | Elapsed time `t`, state `SPEAKING`/`LISTENING`| Simulated speech modulation envelopes | Active only when input signal < 0.03 | lines 639-653, 1576-1597 |
| 13| Audio | Zero-Re-Render WS Audio Blend | Mutable audio level bridge bypassing React component re-renders | `jarvisRealtimeRef.audioLevel` | High-frequency 60 FPS audio reactive scale | Safe fallback to 0 | sphere.tsx:319-324 |
| 14| UI / Event | Window CustomEvent Bridge | Bidirectional event dispatching for Electron runtime | `jarvis-state` CustomEvent | State synchronization across UI and 3D scene | Ignores invalid states | lines 580-587, 1201-1206 |
| 15| UI / Event | Keyboard Navigation | Quick state testing via numeric keys `1`-`9`, `0`, `-` | Keydown events | Dispatches `jarvis-state` | Guards against inputs/textareas | lines 1208-1222 |
| 16| Interaction| Orbit Rotation & Pointer Drag | Interactive mouse/touch camera drag with damping | Pointerdown, pointermove, pointerup | `rootGroup.rotation` X and Y | Clamps pitch between -1.1 and 1.1 rad | lines 1245-1267, 1609-1612 |
| 17| Postprocess| Procedural Texture Generation | Canvas-based smooth radial gradients for glow and backdrop | HTML5 2D Canvas API | `CanvasTexture` for glow and contrast halo | Disposed cleanly on unmount | lines 429-470, 1285-1321 |

---

## 3. The 11 Holographic Core States Specification

Below is the definitive catalog of all 11 holographic states, including exact color definitions, mathematical displacement equations, ring animations, and lighting/glow parameters.

```
State Palette Spectrum:
[1] IDLE           #67e8f9  Ice-Cyan        ● (Calm breathing wave)
[2] LISTENING      #00f0ff  Sky-Cyan        ● (Inward contraction + sonar ripples)
[3] THINKING       #fbbf24  Amber-Gold      ● (Hemisphere twist + fast gyroscopes)
[4] SPEAKING       #e0f2fe  White-Ice       ● (Bass punch + mid waves + corona)
[5] WEB_SEARCH     #38bdf8  Cyber Azure     ● (23.5° tilted globe + radar sweep)
[6] DEEP_RESEARCH  #818cf8  Periwinkle      ● (3 nested counter-rotating shells)
[7] CODING         #4ade80  Matrix Mint     ● (Beveled holo-cube + falling code)
[8] VISION_SCAN    #f472b6  Laser Rose      ● (Optical lidar ring + polar sweep)
[9] MEMORY_SYNC    #2dd4bf  Teal-Cyan       ● (Arc-Reactor torus + poloidal flow)
[0] EXECUTING_TOOL #c084fc  Neon Violet     ● (Multi-axis spin + octupole facets)
[-] ALERT          #fb7185  Crimson-Coral   ● (Lub-dub twin cardiac shockwave)
```

### Detailed State Specifications

#### State 1: `IDLE`
- **Key Binding**: `[1]`
- **State Identifier**: `'IDLE'`
- **Color Name**: Ice-Cyan
- **Hex Code**: `#67e8f9` | **RGB Normalized**: `(0.404, 0.910, 0.976)`
- **Visual Description**: Calm breathing surface wave, slow axial drift, soft dual rings.
- **Rotation Vector**:
  $$\Delta \text{rot}_y = dt \times 0.15$$
  $$\text{target\_rot}_x = \sin(t \times 0.4) \times 0.08$$
  $$\Delta \text{rot}_z = dt \times 0.04$$
- **Core Glow Dynamics**:
  $$\text{scale} = 2.45 + w_{\text{IDLE}} \times \sin(t \times 1.6) \times 0.15$$
  $$\text{opacity} = 0.36$$
- **Gyroscopic Rings**:
  - Speed Multiplier: $0.25$
  - Ring 1 Opacity: $0.22 \times w_{\text{IDLE}}$
  - Ring 2 Opacity: $0.22 \times 0.78 \times w_{\text{IDLE}} \approx 0.1716$
  - Ring 3: Inactive ($\text{opacity} = 0$)
- **Particle Displacement**:
  $$\text{disp}_{\text{IDLE}} = \sin(t \times 1.6) \times 0.035 + \sin(n_x \times 2.5 + t \times 1.1) \cos(n_y \times 2.5 - t \times 0.9) \times 0.03$$
- **Extra Highlight**: $0.0$

---

#### State 2: `LISTENING`
- **Key Binding**: `[2]`
- **State Identifier**: `'LISTENING'`
- **Color Name**: Sky-Cyan
- **Hex Code**: `#00f0ff` | **RGB Normalized**: `(0.000, 0.941, 1.000)`
- **Visual Description**: Inward focus contraction + concentric equatorial-to-polar sonar ripples + live mic reactivity.
- **Rotation Vector**:
  $$\Delta \text{rot}_y = dt \times 0.18$$
  $$\text{target\_rot}_x = 0.08, \quad \text{target\_rot}_z = 0.0$$
- **Core Glow Dynamics**:
  $$\text{scale} = 2.45 + w_{\text{LISTENING}} \times (0.25 + \text{bass} \times 0.7)$$
  $$\text{opacity} = 0.36$$
- **Gyroscopic Rings**:
  - Speed Multiplier: $0.60$
  - Ring 1 Opacity: $0.50 \times w_{\text{LISTENING}}$
  - Ring 1 Scale: $1.0 + w_{\text{LISTENING}} \times \text{bass} \times 0.08$
  - Ring 2 Opacity: $0.50 \times 0.78 \times w_{\text{LISTENING}} = 0.39$
  - Ring 3: Inactive ($\text{opacity} = 0$)
- **Particle Displacement**:
  $$\text{disp}_{\text{LISTENING}} = -0.07 + \sin(|n_y| \times 10.0 - t \times 6.5) \times 0.085 + \text{bass} \times 0.24 + \text{mid} \times 0.18 \sin(n_y \times 14.0 - t \times 10.0)$$
  *(Note: The $-0.07$ baseline represents physical sphere contraction into an attentive listening mode).*
- **Audio Boost**: Live raw audio signals are amplified by $2.2\times$ in LISTENING state. If raw audio is absent, an attentive pulse is generated:
  $$\text{pulse} = \max(0, \sin(t \times 3.8) \times 0.5 + \sin(t \times 6.3) \times 0.3)$$
  $$\text{rawBass} = 0.10 + \text{pulse} \times 0.32, \quad \text{rawMid} = 0.08 + \text{pulse} \times 0.28, \quad \text{rawTreble} = 0.05 + \text{pulse} \times 0.20$$

---

#### State 3: `THINKING`
- **Key Binding**: `[3]`
- **State Identifier**: `'THINKING'`
- **Color Name**: Amber-Gold
- **Hex Code**: `#fbbf24` | **RGB Normalized**: `(0.984, 0.749, 0.141)`
- **Visual Description**: Counter-twisting hemisphere vortex + 3D spherical-harmonic lobes + fast gyroscope rings.
- **Rotation Vector**:
  $$\Delta \text{rot}_y = dt \times 0.72, \quad \Delta \text{rot}_x = dt \times 0.32, \quad \Delta \text{rot}_z = dt \times 0.24$$
- **Core Glow Dynamics**:
  $$\text{scale} = 2.45 + w_{\text{THINKING}} \times (0.35 + \sin(t \times 6.0) \times 0.28)$$
  $$\text{opacity} = 0.36 + w_{\text{THINKING}} \times 0.14 = 0.50$$
- **Gyroscopic Rings**:
  - Speed Multiplier: $2.40$ (rapid gyro spinning)
  - Ring 1 Opacity: $0.65 \times w_{\text{THINKING}}$
  - Ring 2 Opacity: $0.65 \times 0.78 \times w_{\text{THINKING}} \approx 0.507$
- **Hemisphere Vortex Twist**:
  $$\text{twist} = w_{\text{THINKING}} \times (n_y \times 2.1 \sin(t \times 2.0) + \sin(t \times 1.6 + \text{phase} \times 0.4) \times 0.55)$$
  $$d_x = n_x \cos(\text{twist}) - n_z \sin(\text{twist})$$
  $$d_z = n_x \sin(\text{twist}) + n_z \cos(\text{twist})$$
- **Spherical-Harmonic Particle Displacement**:
  $$\text{disp}_{\text{THINKING}} = \sin(d_x \times 4.0 + t \times 4.5) \cos(d_y \times 4.0 - t \times 3.8) \sin(d_z \times 4.0 + t \times 3.2) \times 0.22 + \sin(t \times 6.0 + \text{phase}) \times 0.04$$

---

#### State 4: `SPEAKING`
- **Key Binding**: `[4]`
- **State Identifier**: `'SPEAKING'`
- **Color Name**: White-Ice
- **Hex Code**: `#e0f2fe` | **RGB Normalized**: `(0.878, 0.949, 0.996)`
- **Visual Description**: Multi-band audio reactivity (bass core punch, mid standing waves, treble corona spikes).
- **Rotation Vector**:
  $$\Delta \text{rot}_y = dt \times (0.28 + \text{bass} \times 0.65)$$
  $$\text{target\_rot}_x = \sin(t \times 1.8) \times 0.15$$
  $$\Delta \text{rot}_z = dt \times 0.08$$
- **Core Glow Dynamics**:
  $$\text{scale} = 2.45 + w_{\text{SPEAKING}} \times (0.45 + \text{bass} \times 1.15)$$
  $$\text{opacity} = 0.36 + w_{\text{SPEAKING}} \times (0.20 + \text{bass} \times 0.28)$$
- **Gyroscopic Rings**:
  - Speed Multiplier: $0.90$
  - Ring 1 Opacity: $0.55 \times w_{\text{SPEAKING}}$
  - Ring 1 Scale: $1.0 + w_{\text{SPEAKING}} \times \text{bass} \times 0.16$
  - Ring 2 Scale: $1.0 + w_{\text{SPEAKING}} \times \text{mid} \times 0.14$
- **Particle Displacement**:
  $$\text{disp}_{\text{SPEAKING}} = \text{bass} \times 0.25 + \sin(n_x \times 5.0 + t \times 11.0) \cos(n_y \times 5.0 - t \times 9.0) \times (0.07 + \text{mid} \times 0.26) + \text{spread} \times \text{treble} \times 0.44$$
- **Color Crest Boost**:
  $$\text{crest} \mathrel{+}= w_{\text{SPEAKING}} \times \text{bass} \times 0.45$$
- **Speech Cadence Synthesizer Fallback** (when audio input $< 0.03$):
  $$\text{syllable} = \left(\max(0, \sin(t \times 7.2) \times 0.65 + \sin(t \times 11.7) \times 0.35)\right)^{1.4}$$
  $$\text{cadence} = 0.45 + 0.55 \times \max(0, \sin(t \times 2.1 + 0.5))$$
  $$\text{rawBass} = 0.22 + \text{syllable} \times \text{cadence} \times 0.65$$
  $$\text{rawMid} = 0.18 + |\sin(t \times 9.5)| \times \text{cadence} \times 0.58$$
  $$\text{rawTreble} = 0.14 + |\cos(t \times 14.3)| \times \text{cadence} \times 0.52$$

---

#### State 5: `WEB_SEARCH`
- **Key Binding**: `[5]`
- **State Identifier**: `'WEB_SEARCH'`
- **Color Name**: Cyber Azure
- **Hex Code**: `#38bdf8` | **RGB Normalized**: `(0.220, 0.741, 0.973)`
- **Visual Description**: 3D planetary lat/lon wireframe globe on a $23.5^\circ$ axial tilt with a sweeping meridian radar beam and live search-hit data pings.
- **Orientation & Axial Tilt**:
  $$\Delta \text{rot}_y = dt \times 0.38$$
  $$\text{target\_rot}_x = 0.18 \text{ rad} \approx 10.3^\circ$$
  $$\text{target\_rot}_z = -0.38 \text{ rad} \approx -21.8^\circ \text{ (axial tilt)}$$
- **Globe Wireframe Target Coordinates**:
  Precomputed across 12 meridians and 8 parallels:
  $$\text{If } i \equiv 0 \pmod 2: \quad \theta_g = \text{round}\left(\frac{\theta}{2\pi / 12}\right) \times \left(\frac{2\pi}{12}\right)$$
  $$\text{If } i \equiv 1 \pmod 2: \quad \phi_g = \text{clamp}\left(\text{round}\left(\frac{\phi}{\pi / 8}\right) \times \left(\frac{\pi}{8}\right), 0.16, \pi - 0.16\right)$$
  $$\vec{g} = (\sin\phi_g \cos\theta_g, \cos\phi_g, \sin\phi_g \sin\theta_g)$$
  $$\vec{n}_{\text{globe}} = 0.18 \vec{n} + 0.82 \vec{g}$$
- **Radar Meridian Beam & Hit Pings**:
  $$\theta_{\text{radar}} = ((t \times 2.4) \bmod 2\pi) - \pi$$
  $$\Delta \theta = |\theta - \theta_{\text{radar}}| \quad (\text{wrapped to } [0, \pi])$$
  $$\text{beam} = \exp\left(-\frac{\Delta \theta^2}{0.09}\right)$$
  $$\text{ping} = \begin{cases} 1.0 & \text{if } \sin(\text{phase} \times 19.0 + \lfloor t \times 4.5 \rfloor \times 3.7) > 0.965 \\ 0.0 & \text{otherwise} \end{cases}$$
  $$\text{disp}_{\text{WEB\_SEARCH}} = \text{beam} \times 0.14 + \text{ping} \times 0.22$$
  $$\text{extraHighlight} \mathrel{+}= w_{\text{WEB\_SEARCH}} \times \min(1.0, \text{beam} \times 0.9 + \text{ping})$$
- **Ring 3 Transformation**:
  $$\text{opacity} = w_{\text{WEB\_SEARCH}} \times 0.45$$
  $$\text{position} = (0, 0, 0), \quad \text{rotation} = \left(\frac{\pi}{2} + 0.18, 0, -0.38\right), \quad \text{scale} = 1.16$$

---

#### State 6: `DEEP_RESEARCH`
- **Key Binding**: `[6]`
- **State Identifier**: `'DEEP_RESEARCH'`
- **Color Name**: Periwinkle
- **Hex Code**: `#818cf8` | **RGB Normalized**: `(0.506, 0.549, 0.973)`
- **Visual Description**: Sphere splits into 3 nested counter-rotating concentric knowledge shells (core, tilted mid-shell, outer halo).
- **Core Glow Dynamics**:
  $$\text{scale} = 2.45 + w_{\text{DEEP\_RESEARCH}} \times (0.35 + \sin(t \times 3.5) \times 0.2)$$
- **Concentric Shell Partitioning**:
  Each particle $i$ is assigned to shell $s = i \bmod 3$:
  - **Shell 0 (Dense Core)**:
    $$\text{scale}_0 = 0.52, \quad \omega_0 = 1.35 \text{ rad/s}$$
  - **Shell 1 (Tilted Mid-Shell)**:
    $$\text{scale}_1 = 0.88, \quad \omega_1 = -0.85 \text{ rad/s (counter-spin)}, \quad \text{tilt}_x = 0.48 \text{ rad} \approx 27.5^\circ$$
  - **Shell 2 (Diffuse Outer Halo)**:
    $$\text{scale}_2 = 1.20, \quad \omega_2 = 0.42 \text{ rad/s}$$
- **Shell Rotation & Morph**:
  $$\text{spin} = \begin{cases} t \times 1.35 & s = 0 \\ -t \times 0.85 & s = 1 \\ t \times 0.42 & s = 2 \end{cases}$$
  $$s_x = (n_x \cos(\text{spin}) - n_z \sin(\text{spin})) \times \text{scale}_s$$
  $$s_y = n_y \times \text{scale}_s$$
  $$s_z = (n_x \sin(\text{spin}) + n_z \cos(\text{spin})) \times \text{scale}_s$$
  For $s = 1$, rotate around X by $0.48$:
  $$s_y' = s_y \cos(0.48) - s_z \sin(0.48), \quad s_z' = s_y \sin(0.48) + s_z \cos(0.48)$$
  $$\vec{d} \mathrel{+}= (\vec{s} - \vec{d}) \times w_{\text{DEEP\_RESEARCH}}$$
  $$\text{extraHighlight} \mathrel{+}= w_{\text{DEEP\_RESEARCH}} \times (0.55 \text{ if } s=0 \text{ else } 0.15)$$
  $$\text{disp}_{\text{DEEP\_RESEARCH}} = \sin(\text{phase} \times 3.0 + t \times 4.2) \times 0.035$$

---

#### State 7: `CODING`
- **Key Binding**: `[7]`
- **State Identifier**: `'CODING'`
- **Color Name**: Matrix Mint
- **Hex Code**: `#4ade80` | **RGB Normalized**: `(0.290, 0.871, 0.502)`
- **Visual Description**: Morphs into a beveled 3D holo-cube with cascading vertical digital code streams down its faces.
- **Orientation**:
  $$\Delta \text{rot}_y = dt \times 0.34, \quad \text{target\_rot}_x = 0.42 \text{ rad}, \quad \text{target\_rot}_z = 0.18 \text{ rad}$$
- **Beveled Holo-Cube Target Geometry**:
  $$m = \max(|n_x|, |n_y|, |n_z|)$$
  $$\vec{c} = \left(\frac{n_x}{m} \times 0.77, \frac{n_y}{m} \times 0.77, \frac{n_z}{m} \times 0.77\right)$$
  $$\vec{n}_{\text{cube}} = 0.16 \vec{n} + 0.84 \vec{c}$$
  $$\text{seed}_i = ((\text{round}(c_x \times 5 + 10) \times 37 + \text{round}(c_z \times 5 + 10) \times 17) \bmod 19) \times 0.55$$
- **Cascading Digital Code Stream**:
  $$\text{stream} = ((1.0 - n_y) \times 1.8 + t \times 1.55 + \text{seed}_i) \bmod 1.0$$
  $$\text{head} = \exp\left(-((stream - 0.12) \times 9.0)^2\right)$$
  $$\text{disp}_{\text{CODING}} = \text{head} \times 0.07$$
  $$\text{extraHighlight} \mathrel{+}= w_{\text{CODING}} \times \text{head} \times 0.95$$

---

#### State 8: `VISION_SCAN`
- **Key Binding**: `[8]`
- **State Identifier**: `'VISION_SCAN'`
- **Color Name**: Laser Rose
- **Hex Code**: `#f472b6` | **RGB Normalized**: `(0.957, 0.447, 0.714)`
- **Visual Description**: Precision horizontal optical lidar ring & laser plane sweeping smoothly from top pole to bottom pole.
- **Lidar Sweep Motion**:
  $$y_{\text{scan}} = \sin(t \times 2.1) \times 0.94$$
  $$r_{\text{slice}} = \sqrt{\max(0.06, 1.0 - y_{\text{scan}}^2)}$$
- **Ring 3 Dynamic Slicing Ring**:
  $$\text{opacity} = w_{\text{VISION\_SCAN}} \times 0.82$$
  $$\text{position} = (0, y_{\text{scan}} \times R_{\text{BASE}}, 0)$$
  $$\text{rotation} = \left(\frac{\pi}{2}, 0, 0\right)$$
  $$\text{scale} = r_{\text{slice}} \times 1.05$$
- **Laser Plane Particle Activation**:
  $$\Delta y = n_y - y_{\text{scan}}$$
  $$\text{band} = \exp\left(-\frac{\Delta y^2}{0.0075}\right)$$
  $$\text{disp}_{\text{VISION\_SCAN}} = \text{band} \times 0.22 - 0.03$$
  $$\text{extraHighlight} \mathrel{+}= w_{\text{VISION\_SCAN}} \times \text{band} \times 1.1$$

---

#### State 9: `MEMORY_SYNC`
- **Key Binding**: `[9]`
- **State Identifier**: `'MEMORY_SYNC'`
- **Color Name**: Teal-Cyan
- **Hex Code**: `#2dd4bf` | **RGB Normalized**: `(0.176, 0.831, 0.749)`
- **Visual Description**: Opens a central polar tunnel into an Arc-Reactor 3D torus with continuous poloidal particle flow.
- **Orientation**:
  $$\Delta \text{rot}_y = dt \times 0.32, \quad \text{target\_rot}_x = 0.58 \text{ rad}, \quad \text{target\_rot}_z = \sin(t \times 0.6) \times 0.12$$
- **Core Glow Contraction (Polar Void)**:
  $$\text{scale} = 2.45 - w_{\text{MEMORY\_SYNC}} \times 0.55$$
  $$\text{opacity} = 0.36 - w_{\text{MEMORY\_SYNC}} \times 0.12$$
  *(Note: The inner glow shrinks to create an open central chamber).*
- **Toroidal Poloidal Particle Flow Transformation**:
  $$\theta_{\text{poloidal}} = \phi \times 2.0 - t \times 2.6$$
  $$r_{\text{torus}} = 0.78 + 0.34 \cos(\theta_{\text{poloidal}})$$
  $$\vec{t}_{\text{pos}} = (r_{\text{torus}} \cos\theta, 0.38 \sin(\theta_{\text{poloidal}}), r_{\text{torus}} \sin\theta)$$
  $$\vec{d} \mathrel{+}= (\vec{t}_{\text{pos}} - \vec{d}) \times w_{\text{MEMORY\_SYNC}}$$
  $$\text{extraHighlight} \mathrel{+}= w_{\text{MEMORY\_SYNC}} \times \max(0.0, -\cos(\theta_{\text{poloidal}}) \times 0.65)$$

---

#### State 10: `EXECUTING_TOOL`
- **Key Binding**: `[0]`
- **State Identifier**: `'EXECUTING_TOOL'`
- **Color Name**: Neon Violet
- **Hex Code**: `#c084fc` | **RGB Normalized**: `(0.753, 0.518, 0.988)`
- **Visual Description**: High-speed multi-axis spin with crisp octupole geometric facets.
- **High-Speed Multi-Axis Spin**:
  $$\Delta \text{rot}_y = dt \times 0.95, \quad \Delta \text{rot}_z = dt \times 0.45$$
- **Gyroscopic Rings**:
  - Speed Multiplier: $2.80$ (maximum velocity)
  - Ring 1 Opacity: $0.65 \times w_{\text{EXECUTING\_TOOL}}$
- **Octupole Geometric Facets Displacement**:
  $$\text{disp}_{\text{TOOL}} = \sin(n_x \times 7.0 + t \times 4.0) \sin(n_y \times 7.0 - t \times 4.0) \sin(n_z \times 7.0) \times 0.16 + \sin(t \times 8.0) \times 0.05$$

---

#### State 11: `ALERT`
- **Key Binding**: `[-]`
- **State Identifier**: `'ALERT'`
- **Color Name**: Crimson-Coral
- **Hex Code**: `#fb7185` | **RGB Normalized**: `(0.984, 0.443, 0.522)`
- **Visual Description**: Urgent twin-beat cardiac shockwave (lub-dub) with sharp radial warning spikes.
- **Rapid Jitter & Rotation**:
  $$\Delta \text{rot}_y = dt \times 0.55$$
  $$\text{target\_rot}_x = \sin(t \times 9.0) \times 0.06 \text{ (rapid alarm vibration)}$$
- **Twin-Beat Cardiac Shockwave (Lub-Dub)**:
  $$\tau = (t \times 1.18) \bmod 1.0$$
  $$\text{beat} = \exp\left(-((\tau - 0.12) \times 14.0)^2\right) + 0.68 \exp\left(-((\tau - 0.30) \times 16.0)^2\right)$$
- **Core Glow & Ring Alarm Pulse**:
  $$\text{scale}_{\text{core}} = 2.45 + w_{\text{ALERT}} \times \text{beat} \times 0.95$$
  $$\text{opacity}_{\text{core}} = 0.36 + w_{\text{ALERT}} \times \text{beat} \times 0.35$$
  $$\text{opacity}_{\text{rings}} = (0.45 + \text{beat} \times 0.45) \times w_{\text{ALERT}}$$
  $$\text{scale}_{\text{ring1}} = 1.0 + w_{\text{ALERT}} \times \text{beat} \times 0.12$$
- **Radial Spikes Particle Displacement**:
  $$\text{disp}_{\text{ALERT}} = \text{beat} \times (0.18 + \text{spread} \times 0.26) + \sin(n_x \times 9.0) \cos(n_y \times 9.0) \times \text{beat} \times 0.12$$
- **Crest Shockwave**:
  $$\text{crest} \mathrel{+}= w_{\text{ALERT}} \times \text{beat} \times 0.55$$

---

## 4. State Parameters Reference Matrix

| State Name | Key | Hex Code | Base Radius | Core Scale | Core Opacity | Ring Speed | Ring 1 Opacity | Ring 3 Mode | Primary Morph Formula |
|---|---|---|---|---|---|---|---|---|---|
| `IDLE` | `1` | `#67e8f9` | 1.72 | $2.45 + 0.15\sin(1.6t)$ | 0.36 | 0.25 | 0.22 | Off | Dual surface sinusoidal wave |
| `LISTENING` | `2` | `#00f0ff` | 1.72 | $2.45 + 0.25 + 0.7\text{bass}$ | 0.36 | 0.60 | 0.50 | Off | $-0.07$ contraction + sonar ripples |
| `THINKING` | `3` | `#fbbf24` | 1.72 | $2.45 + 0.35 + 0.28\sin(6t)$| 0.50 | 2.40 | 0.65 | Off | Counter-twist vortex + 3D harmonics |
| `SPEAKING` | `4` | `#e0f2fe` | 1.72 | $2.45 + 0.45 + 1.15\text{bass}$| $0.36 + 0.28\text{bass}$ | 0.90 | 0.55 | Off | Bass core punch + mid waves + corona |
| `WEB_SEARCH` | `5` | `#38bdf8` | 1.72 | $2.70$ | 0.36 | 1.15 | 0.62 | Radar Ref | Lat/Lon quantized globe + radar sweep |
| `DEEP_RESEARCH` | `6` | `#818cf8` | 1.72 | $2.45 + 0.35 + 0.2\sin(3.5t)$| 0.36 | 1.50 | 0.55 | Off | 3 nested concentric counter-spinning shells |
| `CODING` | `7` | `#4ade80` | 1.72 | $2.45$ | 0.36 | 0.70 | 0.48 | Off | Beveled cube + falling code stream |
| `VISION_SCAN` | `8` | `#f472b6` | 1.72 | $2.45$ | 0.36 | 0.40 | 0.38 | Lidar Slice| Sweeping lidar slice ring + laser plane |
| `MEMORY_SYNC` | `9` | `#2dd4bf` | 1.72 | $1.90$ (void tunnel) | 0.24 | 1.30 | 0.52 | Off | Arc-Reactor 3D torus + poloidal flow |
| `EXECUTING_TOOL`| `0` | `#c084fc` | 1.72 | $2.45$ | 0.36 | 2.80 | 0.65 | Off | Fast multi-axis spin + octupole facets |
| `ALERT` | `-` | `#fb7185` | 1.72 | $2.45 + 0.95\text{beat}$ | $0.36 + 0.35\text{beat}$ | 2.20 | $0.45 + 0.45\text{beat}$ | Off | Twin-beat cardiac shockwave + spikes |

---

## 5. Three.js Objects, Geometries, Materials & Shaders

### 5.1 Scene Hierarchy & Layering

The visualizer uses a 4-layer composition within a root `THREE.Group`:

```
THREE.Scene
 └── rootGroup (THREE.Group) [Damped User Orbit Rotation Applied Here]
      ├── [Layer 0, renderOrder=0] Backdrop Sprite (Dark Contrast Halo)
      │    └── SpriteMaterial (CanvasTexture: Dark Indigo Radial Gradient)
      ├── [Layer 1, renderOrder=1] Core Glow Sprite (Volumetric Inner Energy)
      │    └── SpriteMaterial (CanvasTexture: White/Cyan Additive Radial Gradient)
      ├── [Layer 2, renderOrder=2] Gyroscopic Rings
      │    ├── ring1 (TorusGeometry: 2.06, 0.010, 12, 144) - MeshBasicMaterial
      │    ├── ring2 (TorusGeometry: 2.19, 0.007, 12, 144) - MeshBasicMaterial
      │    └── ring3 (TorusGeometry: 1.74, 0.012, 12, 144) - MeshBasicMaterial [Dynamic Lidar/Radar]
      └── [Layer 3, renderOrder=3] Morphing Particle Cloud (THREE.Points)
           ├── THREE.BufferGeometry (attributes: position, color)
           └── THREE.PointsMaterial (AdditiveBlending, vertexColors, sizeAttenuation)
```

### 5.2 Procedural Texture Generation

To avoid external asset loading (PNGs) and eliminate network latency, two procedural textures are created dynamically using the HTML5 2D Canvas API:

1. **Glow Texture (64x64 Canvas)**:
   - Center $(32, 32)$, radius $32$.
   - Radial gradient color stops:
     - `0.00`: `rgba(255, 255, 255, 1.0)`
     - `0.22`: `rgba(255, 255, 255, 0.86)`
     - `0.55`: `rgba(255, 255, 255, 0.22)`
     - `1.00`: `rgba(255, 255, 255, 0.0)`
   - Used for: Volumetric core glow sprite and particle point sprite.

2. **Backdrop Texture (128x128 Canvas)**:
   - Center $(64, 64)$, radius $64$.
   - Radial gradient color stops:
     - `0.00`: `rgba(2, 8, 22, 0.88)`
     - `0.48`: `rgba(3, 12, 28, 0.70)`
     - `0.76`: `rgba(3, 12, 28, 0.24)`
     - `1.00`: `rgba(0, 0, 0, 0.0)`
   - Used for: Backdrop contrast halo sprite behind the holographic core.

### 5.3 Particle Buffer Attributes

The particle cloud (`THREE.Points`) allocates static precomputed geometry buffers and dynamically updates `position` and `color` in the animation loop:

```typescript
// Precomputed Static Buffers
positions: Float32Array(count * 3)       // Dynamic active positions
colors: Float32Array(count * 3)          // Dynamic active RGB colors
normals: Float32Array(count * 3)         // Fibonacci sphere unit normals
globeNormals: Float32Array(count * 3)    // Precomputed lat/lon globe targets
cubeNormals: Float32Array(count * 3)     // Precomputed beveled cube targets
thetas: Float32Array(count)              // Spherical theta angles in [-pi, pi]
phis: Float32Array(count)                // Spherical phi angles in [0, pi]
phases: Float32Array(count)              // Random phase offsets [0, 2pi]
spreads: Float32Array(count)             // Uniform random values [0, 1]
colSeeds: Float32Array(count)            // Deterministic spatial seeds for digital code stream
```

### 5.4 Points Material Configuration

```typescript
new THREE.PointsMaterial({
  map: glowTexture,
  size: 0.082,
  vertexColors: true,
  transparent: true,
  opacity: 0.96,
  sizeAttenuation: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
  toneMapped: false,
})
```

### 5.5 Canvas & WebGL Configuration

- **Field of View (FOV)**: $58^\circ$
- **Camera Position**: $(0, 0, 5.1)$
- **Device Pixel Ratio (DPR)**: Clamped between $1.0$ and $2.0$ (`dpr={[1, 2]}`)
- **WebGLRenderer Options**:
  ```typescript
  {
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
    stencil: false,
  }
  ```

---

## 6. State Transition Mechanics & Easing Functions

Transitions between visualizer states are governed by an **exponential damping decay formula**:

$$\text{damp} = 1 - \exp(-k \times dt)$$

Where:
- $dt = \min(0.05, \Delta t)$ — clamped to a maximum of 50 ms to prevent visual explosion after background tab suspension.
- For State Weight Morphing: $k = 6.2$ (yielding a half-life of $t_{1/2} = \frac{\ln 2}{6.2} \approx 112\text{ ms}$, with full visual transition settling in $\sim 350-400\text{ ms}$).
- For Audio Smoothing: $k = 14.0$ (yielding a fast half-life of $\sim 50\text{ ms}$ for responsive yet smooth audio reactivity).

### Multi-Weight Concurrency
All 11 state weights are updated every frame:
$$w_{\text{key}} \leftarrow w_{\text{key}} + ((\text{active} == \text{key} \,?\, 1 : 0) - w_{\text{key}}) \times \text{damp}$$

This allows continuous multi-state cross-blending without snapping, ensuring that even rapid event firing produces a graceful, organic transition.

### Color Interpolation
$$\vec{C}_{\text{blended}} = \text{THREE.Color.lerp}(\vec{C}_{\text{palette}[\text{active}]}, \text{damp})$$

---

## 7. Audio Reactivity Engine & Multi-Band Analysis

The visualizer extracts three frequency bands from an audio input stream (or the unified WebSocket amplitude stream):

```
FFT 256 Spectrum (128 bins total @ 44.1 kHz):
├── BASS   : Bins [0..15]   (~0 Hz to ~1,378 Hz)  -> Controls core pulse, ring 1 scale
├── MID    : Bins [16..55]  (~1,378 Hz to ~4,823 Hz) -> Controls surface standing waves, ring 2 scale
└── TREBLE : Bins [56..111] (~4,823 Hz to ~9,646 Hz) -> Controls corona spikes and outer sparkles
```

### Dual Audio Source Strategy
1. **Primary**: Live Web Audio `AnalyserNode` connected to microphone stream or TTS output stream (`jarvisService.analyser`).
2. **Realtime WebSocket Amplitude Bridge**: Directly reads `jarvisRealtimeRef.audioLevel` inside the animation frame (`useFrame`), blending into the bass/mid/treble bands without triggering React re-renders.
3. **Synthetic Cadence Synthesizer Fallback**: When audio amplitude drops below threshold ($< 0.03$) while in `SPEAKING` state, an autonomous speech cadence generator activates to preserve lifelike visual dynamics.

---

## 8. Interactive Controls & Event Listeners

1. **CustomEvent `jarvis-state`**:
   The primary IPC / frontend communication channel:
   ```javascript
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'THINKING' }));
   ```
2. **Keyboard Controls**:
   Hotkeys `1` to `9`, `0`, and `-` map directly to the 11 states. Input elements (`INPUT`, `TEXTAREA`, `contentEditable`) are safely ignored.
3. **Orbit Rotation Drag**:
   Pointerdown/move/up events calculate user yaw ($\Delta X \times 0.005$) and pitch ($\Delta Y \times 0.005$, clamped to $[-1.1, 1.1]$ rad), which is smoothly damped onto `rootGroup.rotation`.
4. **Particle Density Switcher**:
   Supports runtime switching between 1,800, 2,600, and 3,800 particles by rebuilding the BufferGeometry attributes.

---

## 9. External Dependencies & React/Electron Environment Mapping

| Feature / Dependency | HTML Visualizer Source | React/Electron Equivalent Package | Status in Project |
|---|---|---|---|
| 3D WebGL Library | Three.js r128 CDN | `three` (v0.180.0) | Installed |
| React 3D Fiber | Vanilla Three.js | `@react-three/fiber` (v9.6.1) | Installed |
| 3D Helpers & Drei | Vanilla Three.js | `@react-three/drei` (v10.7.7) | Installed |
| UI Icons | Inline SVG / CSS | `lucide-react` / `react-icons` | Installed |
| Typography | Google Fonts (Inter, JetBrains Mono) | Inter / JetBrains Mono in CSS | Configured |
| Audio Analysis | Web Audio API (`AnalyserNode`) | Native Web Audio API / `jarvisService` | Configured |

---

## 10. Runtime Event Mapping: Electron App Events to the 11 Visualizer States

To fulfill Requirement R2, the 11 visual states are mapped to runtime application events as follows:

| # | Visualizer State | Runtime Trigger Condition | Source Event / Protocol Type |
|---|---|---|---|
| 1 | `IDLE` | App idle, standby, conversation complete, or mic muted with no pending tasks | `agent.state` (`idle`), `jarvis-bridge-status` |
| 2 | `LISTENING` | User speech detected, mic unmuted, wake word triggered ("Hey Jarvis") | `voice:start`, `wake_word_detected`, `agent.state` (`listening`) |
| 3 | `THINKING` | LLM reasoning turn in progress, prompt synthesis, context compression | `agent.state` (`thinking`), `context_compressing` |
| 4 | `SPEAKING` | TTS audio playback active, token streaming with audio synthesis | `agent.state` (`speaking`), `voice_state.is_speaking=true` |
| 5 | `WEB_SEARCH` | Tool execution: `web_search`, `tavily_search`, `brave_search`, `duckduckgo` | `tool.start` with tool matching search patterns |
| 6 | `DEEP_RESEARCH` | Tool execution: `research_deep`, academic paper retrieval, multi-turn RAG | `tool.start` with tool matching research/rag patterns |
| 7 | `CODING` | Code generation, terminal command execution, file editing | `tool.start` with `write_file`, `execute_command`, `git_*` |
| 8 | `VISION_SCAN` | Camera vision active, screen capture desktop analysis, facial detection | `visionMode !== 'none'`, face detection interval active |
| 9 | `MEMORY_SYNC` | HybridMemory RAG indexing, SessionDB vacuum, instincts sync | `tool.start` with `core_memory`, `memory_sync` |
| 10| `EXECUTING_TOOL` | Generic tool execution, Windows MCP actions, nut.js OSWorld automation | `tool.start` default fallback when specific state not matched |
| 11| `ALERT` | AgentShield security block, hardware overheat ($>85^\circ\text{C}$), battery critical ($<10\%$) | `security:blocked`, `system:alert`, error envelopes |

---

## 11. Edge Cases Discovered

| # | Feature | Input / Condition | Observed Behavior & Safe Mitigation |
|---|---------|-------------------|--------------------------------------|
| 1 | State Morphing | Rapid succession of conflicting state events | Multi-weight damped vector prevents snapping; each weight lerps independently with zero visual popping. |
| 2 | Time Discontinuity | Window tab minimized / CPU throttle causing large $\Delta t$ | Delta is hard-clamped via `dt = Math.min(0.05, delta)` to prevent particle coordinate explosions. |
| 3 | Audio Underflow | No microphone permission or silence during `SPEAKING` | Cadence synthesizer fallback generates pseudo-speech modulation, ensuring visualizer remains alive. |
| 4 | WebGL Context Loss | High GPU load or driver restart | Texture cleanup registered in `useEffect` cleanup hook; no uncollected WebGL texture leaks. |
| 5 | React Re-Renders | High frequency 60 FPS audio amplitude stream | Bypasses React state completely; uses `jarvisRealtimeRef` mutable store read directly inside `useFrame`. |
| 6 | Geometry Singularities| Division by zero in spherical math ($\max(|n_x|, |n_y|, |n_z|) = 0$) | Fallback `|| 1` ensures coordinate normalization never divides by zero. |

---

## 12. Recommended TypeScript/React Component Architecture

To replace the existing `src/components/dashboard/sphere.tsx` cleanly and maintain 100% backward compatibility with `src/pages/dashboard.tsx`:

1. **Maintain Interface Parity**:
   ```typescript
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

   export interface ParticleSphereProps {
     count?: number;
   }
   ```
2. **Preserve Export Signature**:
   Export both named `export const Sphere` and default `export default Sphere` so all existing imports in `dashboard.tsx` continue to work without modification.
3. **Zero-Re-Render Animation Loop**:
   Wrap the component with `React.memo(SphereComponent, () => true)` and execute all 3D state updates inside R3F's `useFrame` callback.
4. **Integrated Event Hub Listener**:
   Register a listener for `jarvis-state`, `jarvis-tool-call`, and keyboard events directly within `useEffect` inside the sphere component.

---
*End of Technical Specification Report.*
