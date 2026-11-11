# Technical Specification: 4 Core Visual Layers, Geometry Math, & Shaders

**Document Version**: 1.0.0  
**Source Specification**: `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html` (Authoritative source)  
**Target Environment**: J.A.R.V.I.S Electron App (`e:\Projects\J.A.R.V.I.S Electron App`)  
**Target Subsystem**: `src/components/dashboard/holographic-core/` & `src/components/dashboard/sphere.tsx`  
**Milestone**: Milestone 1 (Visualizer Component Replacement)  
**Investigator**: Explorer Agent (`explorer_m1_layers_1`)  
**Date**: November 11, 2026  

---

## 1. Executive Summary & Scene Architecture

The J.A.R.V.I.S. 3D Holographic Core visualizer employs a depth-composited 4-layer optical pipeline rendered inside a Three.js / React Three Fiber scene graph. All layers are rendered within a primary container (`rootGroup: THREE.Group`) that supports interactive pointer drag orbit rotation with pitch clamping.

To prevent z-fighting, visual clipping, and depth occlusion artifacts inherent to complex semi-transparent volumetric holograms, **every layer enforces `depthWrite: false` and `toneMapped: false`**, using strict `renderOrder` priority sorting from background to foreground:

```
THREE.Scene
 └── rootGroup (THREE.Group) [Damped User Orbit Pitch/Yaw Drag]
      ├── [Layer 0, renderOrder=0] Contrast Backdrop Halo (THREE.Sprite)
      │    └── THREE.SpriteMaterial (CanvasTexture: 128x128 Dark Indigo Radial Gradient)
      ├── [Layer 1, renderOrder=1] Volumetric Core Glow (THREE.Sprite)
      │    └── THREE.SpriteMaterial (CanvasTexture: 64x64 Additive Radial Gradient, Dynamic Scale/Opacity)
      ├── [Layer 2, renderOrder=2] Gyroscopic & Scanner Rings (THREE.Group / Meshes)
      │    ├── ring1 (THREE.Mesh: TorusGeometry 2.06 x 0.010) - MeshBasicMaterial
      │    ├── ring2 (THREE.Mesh: TorusGeometry 2.19 x 0.007) - MeshBasicMaterial
      │    └── ring3 (THREE.Mesh: TorusGeometry 1.74 x 0.012) - MeshBasicMaterial [Dynamic Lidar / Radar]
      └── [Layer 3, renderOrder=3] Fibonacci Particle Cloud (THREE.Points)
           ├── THREE.BufferGeometry (attributes: position, color)
           └── THREE.PointsMaterial (AdditiveBlending, vertexColors, sizeAttenuation, map=glowTexture)
```

---

## 2. Layer 1: Contrast Backdrop Halo Specification

### 2.1 Purpose & Visual Mechanics
The Contrast Backdrop Halo acts as an optical isolation billboard situated directly behind the core center. It creates a dark, vignette falloff that enhances the perceived luminance and color saturation of additive particle elements, ensuring legibility regardless of the host UI background color or transparency.

### 2.2 Scene Hierarchy & Placement
- **Three.js Class**: `THREE.Sprite`
- **Render Order**: `renderOrder = 0` (first in depth sequence)
- **Position**: `[0, 0, -0.3]` (offset $-0.3$ units along the Z-axis behind the sphere center)
- **Scale**: `[5.15, 5.15, 1.0]` (fixed diameter of $5.15$ units, enclosing the $1.72$ base radius particle sphere by a ratio of $5.15 / (2 \times 1.72) \approx 1.50$)

### 2.3 Procedural Texture Generation Math
- **Canvas Size**: $128 \times 128\text{ px}$ (`bSize = 128`)
- **Center**: $(x_0, y_0) = (64, 64)$
- **Radial Coordinates**: Inner radius $r_0 = 0$, Outer radius $r_1 = 64$
- **Alpha Falloff Gradient Stops**:
  | Stop ($t \in [0, 1]$) | Color String | Hex Equivalent | Description |
  |---|---|---|---|
  | `0.00` | `rgba(2, 8, 22, 0.88)` | `#020816` @ $\alpha = 0.88$ | High density dark navy core |
  | `0.48` | `rgba(3, 12, 28, 0.70)` | `#030c1c` @ $\alpha = 0.70$ | Mid-falloff field |
  | `0.76` | `rgba(3, 12, 28, 0.24)` | `#030c1c` @ $\alpha = 0.24$ | Soft outer edge transition |
  | `1.00` | `rgba(0, 0, 0, 0.00)` | `#000000` @ $\alpha = 0.00$ | Completely transparent boundary |

### 2.4 Material Configuration
```typescript
new THREE.SpriteMaterial({
  map: backdropTexture,
  transparent: true,
  depthWrite: false,
  toneMapped: false,
  blending: THREE.NormalBlending, // Composites dark backdrop over background canvas
})
```

---

## 3. Layer 2: Volumetric Core Glow Specification

### 3.1 Purpose & Visual Mechanics
The Volumetric Core Glow simulates the internal energy source of the holographic reactor. It radiates from the geometric center of the particle cloud, dynamically pulsing with audio amplitude, breathing in idle states, expanding with cardiac shockwaves, and contracting to form a void chamber in toroidal memory sync.

### 3.2 Scene Hierarchy & Placement
- **Three.js Class**: `THREE.Sprite`
- **Render Order**: `renderOrder = 1`
- **Position**: `[0, 0, 0]` (exact center origin)
- **Base Scale**: `[2.45, 2.45, 1.0]`

### 3.3 Procedural Glow Texture Generation Math
- **Canvas Size**: $64 \times 64\text{ px}$ (`gSize = 64`)
- **Center**: $(x_0, y_0) = (32, 32)$
- **Radial Coordinates**: Inner radius $r_0 = 0$, Outer radius $r_1 = 32$
- **Alpha Falloff Gradient Stops**:
  | Stop ($t \in [0, 1]$) | Color String | Alpha ($\alpha$) | Description |
  |---|---|---|---|
  | `0.00` | `rgba(255, 255, 255, 1.00)` | $1.00$ | Pure white saturated plasma center |
  | `0.22` | `rgba(255, 255, 255, 0.86)` | $0.86$ | Intense inner corona |
  | `0.55` | `rgba(255, 255, 255, 0.22)` | $0.22$ | Soft radial glow dissipation |
  | `1.00` | `rgba(255, 255, 255, 0.00)` | $0.00$ | Zero boundary |

*(Note: This identical canvas texture is also reused as the point sprite map for the Layer 4 particle cloud).*

### 3.4 Dynamic Scale & Opacity Modulation Formulas

#### Core Scale Modulation Equation:
$$S_{\text{core}}(t) = 2.45 + \sum_{k \in \text{States}} \Delta S_k$$

Where the per-state scale offsets are:
- **`IDLE`**: $w_{\text{IDLE}} \cdot \sin(1.6 t) \cdot 0.15$
- **`LISTENING`**: $w_{\text{LISTENING}} \cdot (0.25 + 0.70 \cdot \text{bass})$
- **`THINKING`**: $w_{\text{THINKING}} \cdot (0.35 + 0.28 \cdot \sin(6.0 t))$
- **`SPEAKING`**: $w_{\text{SPEAKING}} \cdot (0.45 + 1.15 \cdot \text{bass})$
- **`WEB_SEARCH`**: $w_{\text{WEB\_SEARCH}} \cdot 0.25$
- **`DEEP_RESEARCH`**: $w_{\text{DEEP\_RESEARCH}} \cdot (0.35 + 0.20 \cdot \sin(3.5 t))$
- **`MEMORY_SYNC`**: $-w_{\text{MEMORY\_SYNC}} \cdot 0.55$ *(negative offset creates open polar chamber)*
- **`ALERT`**: $w_{\text{ALERT}} \cdot 0.95 \cdot \text{beat}(t)$
- **`CODING` / `VISION_SCAN` / `EXECUTING_TOOL`**: $0.0$

#### Core Opacity Modulation Equation:
$$\alpha_{\text{core}}(t) = 0.36 + w_{\text{SPEAKING}} \cdot (0.20 + 0.28 \cdot \text{bass}) + w_{\text{THINKING}} \cdot 0.14 + w_{\text{ALERT}} \cdot 0.35 \cdot \text{beat}(t) - w_{\text{MEMORY\_SYNC}} \cdot 0.12$$

Where:
$$\tau(t) = (1.18 t) \bmod 1.0$$
$$\text{beat}(t) = \exp\left(-((\tau - 0.12) \cdot 14.0)^2\right) + 0.68 \exp\left(-((\tau - 0.30) \cdot 16.0)^2\right)$$

#### Color Tinting:
$$\vec{C}_{\text{core}} = \vec{C}_{\text{blended}} \quad \text{where} \quad \vec{C}_{\text{blended}} \leftarrow \text{lerp}(\vec{C}_{\text{palette}[\text{active}]}, 1 - \exp(-6.2 \cdot dt))$$

### 3.5 Material Configuration
```typescript
new THREE.SpriteMaterial({
  map: glowTexture,
  color: blendedColor,
  transparent: true,
  opacity: 0.38, // base opacity, updated per frame
  blending: THREE.AdditiveBlending,
  depthWrite: false,
  toneMapped: false,
})
```

---

## 4. Layer 3: Gyroscopic & Scanner Rings Specification

### 4.1 Ring Topologies & Geometries

The visualizer utilizes three concentric `THREE.TorusGeometry` rings:

| Ring Index | Role | Major Radius ($R$) | Tube Radius ($r$) | Radial Segments | Tubular Segments | Total Vertices |
|---|---|---|---|---|---|---|
| **Ring 1** | Outer Tilted Gyroscope | $2.06$ | $0.010$ | $12$ | $144$ | $1,885$ |
| **Ring 2** | Inner Counter-Rotating | $2.19$ | $0.007$ | $12$ | $144$ | $1,885$ |
| **Ring 3** | Dynamic Lidar / Radar | $1.74$ | $0.012$ | $12$ | $144$ | $1,885$ |

### 4.2 Material & Shader Configuration
All three rings share `THREE.MeshBasicMaterial` instances with additive blending:
- **Ring 1 Material**:
  ```typescript
  new THREE.MeshBasicMaterial({
    color: blendedColor,
    transparent: true,
    opacity: 0.25,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  })
  ```
- **Ring 2 Material**:
  ```typescript
  new THREE.MeshBasicMaterial({
    color: blendedColor,
    transparent: true,
    opacity: 0.20,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  })
  ```
- **Ring 3 Material**:
  ```typescript
  new THREE.MeshBasicMaterial({
    color: new THREE.Color('#ffffff').lerp(blendedColor, 0.35), // Pure white laser core with state tint
    transparent: true,
    opacity: 0.0, // Inactive by default
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  })
  ```

### 4.3 Initial Orientations
- **Ring 1**: `rotation.set(Math.PI * 0.32, 0.2, 0)` ($\approx 57.6^\circ$ pitch, $11.5^\circ$ yaw)
- **Ring 2**: `rotation.set(-Math.PI * 0.25, 0.5, Math.PI * 0.15)` ($\approx -45.0^\circ$ pitch, $28.6^\circ$ yaw, $27.0^\circ$ roll)
- **Ring 3**: `rotation.set(0, 0, 0)`

### 4.4 Gyroscopic Ring Kinematics & Rotation Math

#### State-Weighted Speed Coefficient ($V_{\text{ring}}$):
$$V_{\text{ring}} = 0.25 w_{\text{IDLE}} + 0.60 w_{\text{LISTENING}} + 2.40 w_{\text{THINKING}} + 0.90 w_{\text{SPEAKING}} + 1.15 w_{\text{WEB\_SEARCH}} + 1.50 w_{\text{DEEP\_RESEARCH}} + 0.70 w_{\text{CODING}} + 0.40 w_{\text{VISION\_SCAN}} + 1.30 w_{\text{MEMORY\_SYNC}} + 2.80 w_{\text{EXECUTING\_TOOL}} + 2.20 w_{\text{ALERT}}$$

#### Angular Step Equations:
- **Ring 1**:
  $$\Delta \text{rot}_{1,x} = dt \cdot V_{\text{ring}}$$
  $$\Delta \text{rot}_{1,y} = dt \cdot V_{\text{ring}} \cdot 0.60$$
- **Ring 2 (Counter-Rotation)**:
  $$\Delta \text{rot}_{2,y} = -dt \cdot V_{\text{ring}} \cdot 0.85$$
  $$\Delta \text{rot}_{2,z} = dt \cdot V_{\text{ring}} \cdot 0.55$$

### 4.5 Dynamic Opacity & Audio-Scale Modulation
- **Base Ring Opacity**:
  $$\alpha_{\text{base}} = 0.22 w_{\text{IDLE}} + 0.50 w_{\text{LISTENING}} + 0.65 w_{\text{THINKING}} + 0.55 w_{\text{SPEAKING}} + 0.62 w_{\text{WEB\_SEARCH}} + 0.55 w_{\text{DEEP\_RESEARCH}} + 0.48 w_{\text{CODING}} + 0.38 w_{\text{VISION\_SCAN}} + 0.52 w_{\text{MEMORY\_SYNC}} + 0.65 w_{\text{EXECUTING\_TOOL}} + (0.45 + 0.45 \cdot \text{beat}(t)) w_{\text{ALERT}}$$
  $$\alpha_{\text{ring1}} = \alpha_{\text{base}}$$
  $$\alpha_{\text{ring2}} = \alpha_{\text{base}} \cdot 0.78$$

- **Audio & Heartbeat Scale Expansion**:
  $$S_{\text{ring1}} = 1.0 + 0.16 \cdot w_{\text{SPEAKING}} \cdot \text{bass} + 0.08 \cdot w_{\text{LISTENING}} \cdot \text{bass} + 0.12 \cdot w_{\text{ALERT}} \cdot \text{beat}(t)$$
  $$S_{\text{ring2}} = 1.0 + 0.14 \cdot w_{\text{SPEAKING}} \cdot \text{mid} + 0.08 \cdot w_{\text{DEEP\_RESEARCH}}$$

### 4.6 Ring 3 Dynamic Slicing & Radar Modes

#### Mode A: `VISION_SCAN` Slicing Lidar
Active when $w_{\text{VISION\_SCAN}} > 0.01$:
$$\alpha_{\text{ring3}} = 0.82 \cdot w_{\text{VISION\_SCAN}}$$
$$y_{\text{scan}} = \sin(2.1 t) \cdot 0.94$$
$$r_{\text{slice}} = \sqrt{\max\left(0.06, 1.0 - y_{\text{scan}}^2\right)}$$
$$\text{position} = (0, y_{\text{scan}} \cdot R_{\text{BASE}}, 0) \quad \text{with } R_{\text{BASE}} = 1.72$$
$$\text{rotation} = \left(\frac{\pi}{2}, 0, 0\right)$$
$$\text{scale} = r_{\text{slice}} \cdot 1.05$$

#### Mode B: `WEB_SEARCH` Equatorial Radar Reference Plane
Active when $w_{\text{WEB\_SEARCH}} > 0.01$ (and not in `VISION_SCAN`):
$$\alpha_{\text{ring3}} = 0.45 \cdot w_{\text{WEB\_SEARCH}}$$
$$\text{position} = (0, 0, 0)$$
$$\text{rotation} = \left(\frac{\pi}{2} + 0.18, 0, -0.38\right) \quad (\approx 23.5^\circ\text{ axial tilt})$$
$$\text{scale} = 1.16$$

#### Mode C: Inactive
$$\alpha_{\text{ring3}} = 0.0$$

---

## 5. Layer 4: Fibonacci Particle Cloud Specification

### 5.1 Fibonacci Golden Spiral Sampling Math
The core particle cloud uniformly distributes $N \in \{1800, 2600, 3800\}$ particles (default $N = 2600$) across a unit sphere using the golden section spiral, avoiding polar clustering.

- **Golden Angle**:
  $$\theta_g = \pi \left(3 - \sqrt{5}\right) \approx 2.39996322972865332\text{ rad} \quad (137.507764^\circ)$$

- **Coordinate Generation Algorithm (for $i = 0, \dots, N-1$)**:
  1. Height distribution:
     $$y_i = 1.0 - \left(\frac{i}{\max(1, N - 1)}\right) \cdot 2.0 \quad \in [1.0, -1.0]$$
  2. Horizontal slice radius:
     $$r_i = \sqrt{\max(0.0, 1.0 - y_i^2)}$$
  3. Golden azimuthal angle:
     $$\theta_i = \theta_g \cdot i$$
  4. Unit sphere normal with organic jitter ($\pm 0.0125$):
     $$n_{x,i} = \cos(\theta_i) \cdot r_i + (\text{rand}() - 0.5) \cdot 0.025$$
     $$n_{y,i} = y_i + (\text{rand}() - 0.5) \cdot 0.025$$
     $$n_{z,i} = \sin(\theta_i) \cdot r_i + (\text{rand}() - 0.5) \cdot 0.025$$
     $$\vec{n}_i = \frac{(n_{x,i}, n_{y,i}, n_{z,i})}{\max\left(10^{-6}, \text{hypot}(n_{x,i}, n_{y,i}, n_{z,i})\right)}$$
  5. Base rest position:
     $$\vec{P}_{0,i} = \vec{n}_i \cdot R_{\text{BASE}} \quad \text{with } R_{\text{BASE}} = 1.72$$
  6. Spherical angular properties:
     $$\theta_{\text{sph}, i} = \text{atan2}(n_{z,i}, n_{x,i}) \quad \in [-\pi, \pi]$$
     $$\phi_{\text{sph}, i} = \arccos\left(\text{clamp}(n_{y,i}, -1.0, 1.0)\right) \quad \in [0, \pi]$$
  7. Per-particle stochastic seeds:
     $$\text{phase}_i = \text{rand}() \cdot 2\pi, \quad \text{spread}_i = \text{rand}() \in [0.0, 1.0]$$

### 5.2 Precomputed Morph Target Geometries

#### 1. Quantized Lat/Lon Hologram Globe (`globeNormals`, for `WEB_SEARCH`)
Partitions odd and even particles into longitudinal meridians and latitudinal parallels:
- **Even indices ($i \equiv 0 \pmod 2$, Meridians)**:
  $$M = 12, \quad \Delta\theta = \frac{2\pi}{12} = \frac{\pi}{6}$$
  $$\theta_g = \text{round}\left(\frac{\theta_{\text{sph}, i}}{\Delta\theta}\right) \cdot \Delta\theta, \quad \phi_g = \phi_{\text{sph}, i}$$
- **Odd indices ($i \equiv 1 \pmod 2$, Parallels)**:
  $$P = 8, \quad \Delta\phi = \frac{\pi}{8}$$
  $$\theta_g = \theta_{\text{sph}, i}, \quad \phi_g = \text{clamp}\left(\text{round}\left(\frac{\phi_{\text{sph}, i}}{\Delta\phi}\right) \cdot \Delta\phi, 0.16, \pi - 0.16\right)$$
- **Target Vector**:
  $$\vec{g}_i = (\sin\phi_g \cos\theta_g, \cos\phi_g, \sin\phi_g \sin\theta_g)$$
  $$\vec{n}_{\text{globe}, i} = 0.18 \vec{n}_i + 0.82 \vec{g}_i$$

#### 2. Beveled 3D Holo-Cube Target (`cubeNormals`, for `CODING`)
Projects spherical coordinates onto cube faces normalized to radius $0.77$:
$$m = \max(|n_{x,i}|, |n_{y,i}|, |n_{z,i}|) \quad (\text{fallback to } 1.0)$$
$$\vec{c}_i = \left(\frac{n_{x,i}}{m} \cdot 0.77, \frac{n_{y,i}}{m} \cdot 0.77, \frac{n_{z,i}}{m} \cdot 0.77\right)$$
$$\vec{n}_{\text{cube}, i} = 0.16 \vec{n}_i + 0.84 \vec{c}_i$$

- **Deterministic Matrix Column Seeds (`colSeeds`)**:
  $$q_x = \text{round}(c_{x,i} \cdot 5.0) + 10$$
  $$q_z = \text{round}(c_{z,i} \cdot 5.0) + 10$$
  $$\text{colSeeds}_i = ((q_x \cdot 37 + q_z \cdot 17) \bmod 19) \cdot 0.55$$

### 5.3 Particle Vector Transformations & Displacement Physics

Every frame, each particle initializes its directional normal $\vec{d}_i \leftarrow \vec{n}_i$. Transformations and displacements are computed as follows:

#### 1. `THINKING` Hemisphere Vortex Twist:
When $w_{\text{THINKING}} > 0.001$:
$$\text{twist} = w_{\text{THINKING}} \cdot \left(2.1 n_{y,i} \sin(2.0 t) + 0.55 \sin(1.6 t + 0.4 \text{phase}_i)\right)$$
$$d_{x,i}' = d_{x,i} \cos(\text{twist}) - d_{z,i} \sin(\text{twist})$$
$$d_{z,i}' = d_{x,i} \sin(\text{twist}) + d_{z,i} \cos(\text{twist})$$

#### 2. `WEB_SEARCH` Globe Morph & Radar Beam:
When $w_{\text{WEB\_SEARCH}} > 0.001$:
$$\vec{d}_i \leftarrow \vec{d}_i + (\vec{n}_{\text{globe}, i} - \vec{d}_i) \cdot w_{\text{WEB\_SEARCH}}$$
$$\theta_{\text{radar}} = ((2.4 t) \bmod 2\pi) - \pi$$
$$\Delta\theta = |\theta_{\text{sph}, i} - \theta_{\text{radar}}| \quad (\text{if } \Delta\theta > \pi \implies \Delta\theta = 2\pi - \Delta\theta)$$
$$\text{beam} = \exp\left(-\frac{\Delta\theta^2}{0.09}\right)$$
$$\text{ping} = \begin{cases} 1.0 & \text{if } \sin(19.0 \text{phase}_i + 3.7 \lfloor 4.5 t \rfloor) > 0.965 \\ 0.0 & \text{otherwise} \end{cases}$$
$$\text{webDisp} = 0.14 \cdot \text{beam} + 0.22 \cdot \text{ping}$$
$$\text{extraHighlight} \mathrel{+}= w_{\text{WEB\_SEARCH}} \cdot \min(1.0, 0.9 \cdot \text{beam} + \text{ping})$$

#### 3. `DEEP_RESEARCH` Concentric 3-Shell Partitioning:
When $w_{\text{DEEP\_RESEARCH}} > 0.001$:
Shell assignment: $s = i \bmod 3$
- **Shell 0 (Dense Core)**: $\text{scale}_0 = 0.52, \omega_0 = 1.35\text{ rad/s}$
- **Shell 1 (Tilted Mid-Shell)**: $\text{scale}_1 = 0.88, \omega_1 = -0.85\text{ rad/s}, \text{tilt}_x = 0.48\text{ rad}$
- **Shell 2 (Diffuse Outer Halo)**: $\text{scale}_2 = 1.20, \omega_2 = 0.42\text{ rad/s}$

Rotation around Y:
$$s_x = (n_{x,i} \cos(\omega_s t) - n_{z,i} \sin(\omega_s t)) \cdot \text{scale}_s$$
$$s_y = n_{y,i} \cdot \text{scale}_s$$
$$s_z = (n_{x,i} \sin(\omega_s t) + n_{z,i} \cos(\omega_s t)) \cdot \text{scale}_s$$

For Shell 1 ($s=1$), rotate around X by $0.48\text{ rad}$:
$$s_y' = s_y \cos(0.48) - s_z \sin(0.48)$$
$$s_z' = s_y \sin(0.48) + s_z \cos(0.48)$$

Morph blending:
$$\vec{d}_i \leftarrow \vec{d}_i + (\vec{s}_i - \vec{d}_i) \cdot w_{\text{DEEP\_RESEARCH}}$$
$$\text{extraHighlight} \mathrel{+}= w_{\text{DEEP\_RESEARCH}} \cdot \begin{cases} 0.55 & s=0 \\ 0.15 & s \in \{1, 2\} \end{cases}$$

#### 4. `CODING` Holo-Cube Morph & Falling Matrix Stream:
When $w_{\text{CODING}} > 0.001$:
$$\vec{d}_i \leftarrow \vec{d}_i + (\vec{n}_{\text{cube}, i} - \vec{d}_i) \cdot w_{\text{CODING}}$$
$$\text{stream} = (1.8 (1.0 - n_{y,i}) + 1.55 t + \text{colSeeds}_i) \bmod 1.0$$
$$\text{head} = \exp\left(-((\text{stream} - 0.12) \cdot 9.0)^2\right)$$
$$\text{codeDisp} = 0.07 \cdot \text{head}$$
$$\text{extraHighlight} \mathrel{+}= w_{\text{CODING}} \cdot 0.95 \cdot \text{head}$$

#### 5. `MEMORY_SYNC` Arc-Reactor 3D Torus Poloidal Flow:
When $w_{\text{MEMORY\_SYNC}} > 0.001$:
$$\theta_{\text{poloidal}} = 2.0 \phi_{\text{sph}, i} - 2.6 t$$
$$R_{\text{torus}} = 0.78 + 0.34 \cos(\theta_{\text{poloidal}})$$
$$\vec{t}_{\text{pos}} = \left(R_{\text{torus}} \cos\theta_{\text{sph}, i}, 0.38 \sin(\theta_{\text{poloidal}}), R_{\text{torus}} \sin\theta_{\text{sph}, i}\right)$$
$$\vec{d}_i \leftarrow \vec{d}_i + (\vec{t}_{\text{pos}} - \vec{d}_i) \cdot w_{\text{MEMORY\_SYNC}}$$
$$\text{extraHighlight} \mathrel{+}= w_{\text{MEMORY\_SYNC}} \cdot \max\left(0.0, -0.65 \cos(\theta_{\text{poloidal}})\right)$$

#### 6. Remaining Per-State Radial Displacements:
- **`IDLE`**:
  $$\text{idleDisp} = 0.035 \sin(1.6 t) + 0.03 \sin(2.5 n_{x,i} + 1.1 t) \cos(2.5 n_{y,i} - 0.9 t)$$
- **`LISTENING`**:
  $$\text{listenDisp} = -0.07 + 0.085 \sin(10.0 |n_{y,i}| - 6.5 t) + 0.24 \cdot \text{bass} + 0.18 \cdot \text{mid} \cdot \sin(14.0 n_{y,i} - 10.0 t)$$
- **`THINKING`**:
  $$\text{thinkDisp} = 0.22 \sin(4.0 d_{x,i} + 4.5 t) \cos(4.0 d_{y,i} - 3.8 t) \sin(4.0 d_{z,i} + 3.2 t) + 0.04 \sin(6.0 t + \text{phase}_i)$$
- **`SPEAKING`**:
  $$\text{speakDisp} = 0.25 \cdot \text{bass} + (0.07 + 0.26 \cdot \text{mid}) \sin(5.0 n_{x,i} + 11.0 t) \cos(5.0 n_{y,i} - 9.0 t) + 0.44 \cdot \text{spread}_i \cdot \text{treble}$$
- **`DEEP_RESEARCH`**:
  $$\text{researchDisp} = 0.035 \sin(3.0 \text{phase}_i + 4.2 t)$$
- **`VISION_SCAN`**:
  $$\text{distY} = n_{y,i} - y_{\text{scan}}$$
  $$\text{band} = \exp\left(-\frac{\text{distY}^2}{0.0075}\right)$$
  $$\text{visionDisp} = 0.22 \cdot \text{band} - 0.03$$
  $$\text{extraHighlight} \mathrel{+}= w_{\text{VISION\_SCAN}} \cdot 1.10 \cdot \text{band}$$
- **`EXECUTING_TOOL`**:
  $$\text{toolDisp} = 0.16 \sin(7.0 n_{x,i} + 4.0 t) \sin(7.0 n_{y,i} - 4.0 t) \sin(7.0 n_{z,i}) + 0.05 \sin(8.0 t)$$
- **`ALERT`**:
  $$\text{alertDisp} = \text{beat}(t) \cdot (0.18 + 0.26 \cdot \text{spread}_i) + 0.12 \cdot \text{beat}(t) \sin(9.0 n_{x,i}) \cos(9.0 n_{y,i})$$

#### 7. Cumulative Coordinate Output:
$$D_{\text{total}, i} = \sum_{k \in \text{States}} w_k \cdot \text{disp}_{k, i}$$
$$R_i = R_{\text{BASE}} \cdot \left(1.0 + D_{\text{total}, i}\right) \quad \text{with } R_{\text{BASE}} = 1.72$$
$$\vec{P}_i = \vec{d}_i \cdot R_i$$

### 5.4 Vertex Color Modulation & Crest Dynamics
The vertex colors are computed in linear RGB space:
$$\text{crest}_i = \text{clamp}\left(2.6 \cdot D_{\text{total}, i} + \text{extraHighlight}_i + 0.45 \cdot w_{\text{SPEAKING}} \cdot \text{bass} + 0.55 \cdot w_{\text{ALERT}} \cdot \text{beat}(t) + 0.14, 0.0, 1.0\right)$$
$$\text{twinkle}_i = 0.85 + 0.15 \sin(2.6 t + \text{phase}_i)$$

For each color channel $c \in \{r, g, b\}$:
$$C_{c, i} = \left(s_c + (1.0 - s_c) \cdot \text{crest}_i\right) \cdot \text{twinkle}_i$$
Where $\vec{s} = (s_r, s_g, s_b)$ is the interpolated state palette color `blendedColor`.

### 5.5 Particle Points Material Specification
```typescript
new THREE.PointsMaterial({
  map: glowTexture, // Reuses 64x64 radial canvas texture
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

---

## 6. Mesh Orientation & Camera Kinematics

### 6.1 Interactive Drag Orbit Pitch/Yaw Damping
User pointer drag updates `userRotY` and `userRotX` (clamped between $-1.1$ and $+1.1\text{ rad} \approx \pm 63^\circ$). The `rootGroup` lerps toward these targets at $15\%$ per frame:
$$\text{rootGroup.rotation.x} \leftarrow \text{rootGroup.rotation.x} + (\text{userRotX} - \text{rootGroup.rotation.x}) \cdot 0.15$$
$$\text{rootGroup.rotation.y} \leftarrow \text{rootGroup.rotation.y} + (\text{userRotY} - \text{rootGroup.rotation.y}) \cdot 0.15$$

### 6.2 Per-State Point Cloud Mesh Rotations
The particle mesh (`mesh.current`) applies state-specific angular velocity and axial alignment:

| Active State | $\Delta \text{rot}_y$ (Yaw Speed) | Target $\text{rot}_x$ (Pitch) | Target $\text{rot}_z$ (Roll) |
|---|---|---|---|
| `IDLE` | $+0.15 \cdot dt$ | $\sin(0.4 t) \cdot 0.08$ | $+0.04 \cdot dt$ |
| `LISTENING` | $+0.18 \cdot dt$ | $+0.08$ | $0.00$ |
| `THINKING` | $+0.72 \cdot dt$ | $+0.32 \cdot dt$ | $+0.24 \cdot dt$ |
| `SPEAKING` | $(0.28 + 0.65 \cdot \text{bass}) \cdot dt$ | $\sin(1.8 t) \cdot 0.15$ | $+0.08 \cdot dt$ |
| `WEB_SEARCH` | $+0.38 \cdot dt$ | $+0.18$ | $-0.38$ ($23.5^\circ$ axial tilt) |
| `DEEP_RESEARCH` | $+0.15 \cdot dt$ | $\sin(0.4 t) \cdot 0.08$ | $+0.04 \cdot dt$ |
| `CODING` | $+0.34 \cdot dt$ | $+0.42$ | $+0.18$ |
| `VISION_SCAN` | $+0.18 \cdot dt$ | $+0.08$ | $0.00$ |
| `MEMORY_SYNC` | $+0.32 \cdot dt$ | $+0.58$ | $\sin(0.6 t) \cdot 0.12$ |
| `EXECUTING_TOOL` | $+0.95 \cdot dt$ | Target damp | $+0.45 \cdot dt$ |
| `ALERT` | $+0.55 \cdot dt$ | $\sin(9.0 t) \cdot 0.06$ (alarm jitter) | Target damp |

---

## 7. Data Structures & Buffer Layout Reference

### 7.1 Geometry Buffers (Allocated in `Float32Array`)
```typescript
export interface ParticleGeometryData {
  positions: Float32Array    // [count * 3] dynamic active xyz coordinates (updated per frame)
  colors: Float32Array       // [count * 3] dynamic active rgb floats (updated per frame)
  normals: Float32Array      // [count * 3] static base Fibonacci unit normals
  globeNormals: Float32Array // [count * 3] static lat/lon hologram globe target normals
  cubeNormals: Float32Array  // [count * 3] static beveled holo-cube target normals
  thetas: Float32Array       // [count] spherical theta in [-pi, pi]
  phis: Float32Array         // [count] spherical phi in [0, pi]
  phases: Float32Array       // [count] random phases [0, 2pi]
  spreads: Float32Array      // [count] random uniform [0, 1]
  colSeeds: Float32Array     // [count] digital stream column hash seeds
}
```

### 7.2 State Constants & Palette Mapping
```typescript
export type HolographicState =
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
  | 'ALERT'

export const HOLOGRAPHIC_STATE_COLORS: Record<HolographicState, string> = {
  IDLE: '#67e8f9',           // Ice-Cyan
  LISTENING: '#00f0ff',      // Sky-Cyan
  THINKING: '#fbbf24',       // Amber-Gold
  SPEAKING: '#e0f2fe',       // White-Ice
  WEB_SEARCH: '#38bdf8',     // Cyber Azure
  DEEP_RESEARCH: '#818cf8',  // Periwinkle
  CODING: '#4ade80',         // Matrix Mint
  VISION_SCAN: '#f472b6',    // Laser Rose
  MEMORY_SYNC: '#2dd4bf',    // Teal-Cyan
  EXECUTING_TOOL: '#c084fc', // Neon Violet
  ALERT: '#fb7185',          // Crimson-Coral
}
```

---

## 8. TypeScript Component Architecture for Milestone 1

To replace `src/components/dashboard/sphere.tsx` cleanly and cleanly adhere to the project module standards:

### 8.1 Module Breakdown under `src/components/dashboard/holographic-core/`
1. **`types.ts`**:
   - `HolographicState`, `JarvisVisualState` (alias for backward compatibility).
   - Component props: `SphereProps`, `HolographicCoreProps`.
   - Data structures for geometry buffers, audio bands, state weights.
2. **`constants.ts`**:
   - `HOLOGRAPHIC_STATE_COLORS`, `BASE_RADIUS = 1.72`, `KEY_STATE_MAP`.
   - Gyro ring geometric parameters ($R, r, \text{segments}$).
   - Default weights object.
3. **`procedural-textures.ts`**:
   - Factory function `createProceduralTextures()` returning `{ glowTexture, backdropTexture }`.
   - Texture disposal helper `disposeProceduralTextures()`.
4. **`geometry-math.ts`**:
   - `generateFibonacciSphere(count: number): ParticleGeometryData`.
   - Precomputation of golden-spiral, globe normals, and beveled cube normals.
5. **`HolographicScene.tsx`**:
   - The R3F Canvas contents: `rootGroup`, backdrop sprite, core glow sprite, 3 gyroscopic rings, and `THREE.Points` particle cloud.
   - Zero-re-render `useFrame` animation loop updating displacements, audio reactivity, and ring kinematics.
6. **`index.ts`**:
   - Public API re-export.
7. **`src/components/dashboard/sphere.tsx`**:
   - Drop-in backward-compatible wrapper component maintaining `export const Sphere` and `export default Sphere`.

---

*End of Technical Specification Report.*
