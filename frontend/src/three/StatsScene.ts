import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'

export type CityStat = {
  id: string; name: string; country_code: string; country: string
  lat: number; lon: number; total: number; veg_tagged: number; breakfast: number
}
export type Point = [string, string, number, number, number, string, string | null]
export type Hover = { x: number; y: number; title: string; lines: string[] } | null

const DEG = 2 // world units per degree (Europe view)
const LON0 = 10
const LAT0 = 52
const COSLAT = Math.cos((50 * Math.PI) / 180)
const CITY_SCALE = 10 // metres per world unit (city view)

const VEG_COLORS = [0x64748b, 0xfbbf24, 0x34d399, 0x10ff9a]

function proj(lon: number, lat: number): [number, number] {
  return [(lon - LON0) * COSLAT * DEG, (lat - LAT0) * DEG]
}

function glowTexture(): THREE.Texture {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')!
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  grd.addColorStop(0, 'rgba(255,255,255,1)')
  grd.addColorStop(0.25, 'rgba(255,255,255,.55)')
  grd.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = grd
  g.fillRect(0, 0, 128, 128)
  return new THREE.CanvasTexture(c)
}

export class StatsScene {
  private renderer: THREE.WebGLRenderer
  private scene = new THREE.Scene()
  private camera: THREE.PerspectiveCamera
  private controls: OrbitControls
  private europe = new THREE.Group()
  private city = new THREE.Group()
  private countryMeshes: THREE.Mesh[] = []
  private beacons: { mesh: THREE.Mesh; glow: THREE.Sprite; stat: CityStat; base: number }[] = []
  private lookupMarker: THREE.Group | null = null
  private cityPins: THREE.InstancedMesh | null = null
  private cityPoints: Point[] = []
  private raycaster = new THREE.Raycaster()
  private mouse = new THREE.Vector2(-9, -9)
  private mousePx = { x: 0, y: 0 }
  private camGoal: { pos: THREE.Vector3; target: THREE.Vector3 } | null = null
  private raf = 0
  private clock = new THREE.Clock()
  private glowTex = glowTexture()
  private hoveredCountry: THREE.Mesh | null = null
  private selectedCountry: string | null = null
  private covered = new Set<string>()
  private cityOrigin = { lat: 0, lon: 0 }
  private labelsEl: HTMLDivElement
  private labels: { el: HTMLDivElement; pos: THREE.Vector3 }[] = []
  private lastHoverKey = ''
  mode: 'europe' | 'city' = 'europe'
  showTotals = true
  vegOnly = false

  onHover: (h: Hover) => void = () => {}
  onPickCity: (id: string) => void = () => {}
  onPickCountry: (cc: string) => void = () => {}

  private host: HTMLDivElement

  constructor(host: HTMLDivElement) {
    this.host = host
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setClearColor(0x050913)
    host.appendChild(this.renderer.domElement)
    this.labelsEl = document.createElement('div')
    Object.assign(this.labelsEl.style, { position: 'absolute', inset: '0', pointerEvents: 'none', overflow: 'hidden' })
    host.appendChild(this.labelsEl)

    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000)
    this.camera.position.set(0, 70, 55)
    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.08
    this.controls.maxPolarAngle = Math.PI / 2.15
    this.controls.minDistance = 4
    this.controls.maxDistance = 220
    this.controls.addEventListener('start', () => (this.camGoal = null))

    this.scene.fog = new THREE.FogExp2(0x050913, 0.0045)
    this.scene.add(new THREE.AmbientLight(0x8899bb, 0.9))
    const sun = new THREE.DirectionalLight(0xffffff, 1.6)
    sun.position.set(-40, 80, 40)
    this.scene.add(sun)
    const rim = new THREE.DirectionalLight(0x34d399, 0.5)
    rim.position.set(50, 20, -60)
    this.scene.add(rim)

    // ocean
    const ocean = new THREE.Mesh(
      new THREE.PlaneGeometry(800, 800),
      new THREE.MeshStandardMaterial({ color: 0x07142a, roughness: 0.9, metalness: 0.1 }),
    )
    ocean.rotation.x = -Math.PI / 2
    ocean.position.y = -0.05
    this.europe.add(ocean)
    const grid = new THREE.GridHelper(400, 200, 0x10324a, 0x0b2236)
    grid.position.y = 0
    this.europe.add(grid)

    this.scene.add(this.europe)
    this.scene.add(this.city)
    this.city.visible = false

    const el = this.renderer.domElement
    el.addEventListener('pointermove', this.onMove)
    el.addEventListener('click', this.onClick)
    el.addEventListener('pointerleave', () => { this.mouse.set(-9, -9); this.onHover(null) })
    window.addEventListener('resize', this.resize)
    this.resize()
    this.loop()
  }

  // ---------------------------------------------------------------- europe
  async loadCountries(url: string, coveredCodes: string[]) {
    this.covered = new Set(coveredCodes)
    const geo = await (await fetch(url)).json()
    const borderPts: number[] = []
    for (const f of geo.features) {
      const cc: string = f.properties.ISO2
      const name: string = f.properties.NAME
      const polys: number[][][][] = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates
      const shapes: THREE.Shape[] = []
      for (const poly of polys) {
        const ring = (r: number[][]) => r.map(([lon, lat]) => {
          const [x, y] = proj(Math.min(Math.max(lon, -25), 45), Math.min(Math.max(lat, 34), 72))
          return new THREE.Vector2(x, y)
        })
        const outer = ring(poly[0])
        if (outer.length < 4) continue
        const shape = new THREE.Shape(outer)
        for (const hole of poly.slice(1)) shape.holes.push(new THREE.Path(ring(hole)))
        shapes.push(shape)
        for (let i = 0; i < outer.length - 1; i++) {
          borderPts.push(outer[i].x, outer[i].y, outer[i + 1].x, outer[i + 1].y)
        }
      }
      if (!shapes.length) continue
      const isCovered = this.covered.has(cc)
      const geom = new THREE.ExtrudeGeometry(shapes, { depth: isCovered ? 0.6 : 0.3, bevelEnabled: false })
      const mat = new THREE.MeshStandardMaterial({
        color: isCovered ? 0x164e48 : 0x1a2436, roughness: 0.75, metalness: 0.15,
        emissive: isCovered ? 0x062a22 : 0x000000,
      })
      const mesh = new THREE.Mesh(geom, mat)
      mesh.rotation.x = -Math.PI / 2
      mesh.userData = { cc, name, covered: isCovered, baseColor: mat.color.getHex(), lon: f.properties.LON, lat: f.properties.LAT }
      this.countryMeshes.push(mesh)
      this.europe.add(mesh)
    }
    // borders as one line set, lifted above the extrusion
    const pos: number[] = []
    for (let i = 0; i < borderPts.length; i += 4) {
      pos.push(borderPts[i], 0.62, -borderPts[i + 1], borderPts[i + 2], 0.62, -borderPts[i + 3])
    }
    const bg = new THREE.BufferGeometry()
    bg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
    this.europe.add(new THREE.LineSegments(bg, new THREE.LineBasicMaterial({ color: 0x2dd4bf, transparent: true, opacity: 0.35 })))
  }

  setCities(stats: CityStat[]) {
    for (const b of this.beacons) {
      this.europe.remove(b.mesh, b.glow)
    }
    this.beacons = []
    for (const s of stats) {
      const [x, y] = proj(s.lon, s.lat)
      const h = 0.4 + Math.log10(s.total + 1) * 1.8
      const geom = new THREE.CylinderGeometry(0.28, 0.28, 1, 16)
      geom.translate(0, 0.5, 0)
      const mesh = new THREE.Mesh(geom, new THREE.MeshBasicMaterial({ color: 0x34d399, transparent: true, opacity: 0.9 }))
      mesh.position.set(x, 0.6, -y)
      mesh.scale.y = h
      mesh.userData = { city: s }
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({
        map: this.glowTex, color: 0x34d399, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
      }))
      glow.position.set(x, 0.7, -y)
      glow.scale.setScalar(2.4)
      this.europe.add(mesh, glow)
      this.beacons.push({ mesh, glow, stat: s, base: h })
    }
    this.applyBeaconMode()
  }

  applyBeaconMode() {
    for (const b of this.beacons) {
      const v = this.vegOnly ? b.stat.veg_tagged : b.stat.total
      const h = this.vegOnly ? 0.4 + Math.log10(v + 1) * 2.4 : b.base
      const visible = this.showTotals && (!this.selectedCountry || b.stat.country_code === this.selectedCountry)
      b.mesh.visible = visible
      b.glow.visible = visible
      b.mesh.scale.y = h
      const col = this.vegOnly ? 0x10ff9a : 0x34d399
      ;(b.mesh.material as THREE.MeshBasicMaterial).color.setHex(v > 0 ? col : 0x64748b)
      ;(b.glow.material as THREE.SpriteMaterial).color.setHex(v > 0 ? col : 0x64748b)
    }
    this.refreshLabels()
  }

  focusEurope() {
    this.selectedCountry = null
    this.mode = 'europe'
    this.city.visible = false
    this.europe.visible = true
    this.scene.fog = new THREE.FogExp2(0x050913, 0.0045)
    this.controls.maxDistance = 220
    this.highlightCountries()
    this.applyBeaconMode()
    this.flyTo(new THREE.Vector3(0, 70, 55), new THREE.Vector3(0, 0, 0))
  }

  focusCountry(cc: string) {
    this.selectedCountry = cc
    if (this.mode === 'city') this.exitCity()
    const meshes = this.countryMeshes.filter((m) => m.userData.cc === cc)
    if (!meshes.length) return
    const box = new THREE.Box3()
    meshes.forEach((m) => box.expandByObject(m))
    // only consider beacons for a tighter frame (overseas territories blow up bboxes)
    const cityBox = new THREE.Box3()
    this.beacons.filter((b) => b.stat.country_code === cc).forEach((b) => cityBox.expandByPoint(b.mesh.position))
    const target = (cityBox.isEmpty() ? box : cityBox).getCenter(new THREE.Vector3())
    const size = Math.max(box.getSize(new THREE.Vector3()).x, box.getSize(new THREE.Vector3()).z, 6)
    const d = Math.min(size * 1.15, 40)
    this.highlightCountries()
    this.applyBeaconMode()
    this.flyTo(new THREE.Vector3(target.x, d * 0.95, target.z + d * 0.75), new THREE.Vector3(target.x, 0, target.z))
  }

  showLookup(lat: number, lon: number, total: number) {
    if (this.lookupMarker) this.europe.remove(this.lookupMarker)
    if (this.mode === 'city') this.exitCity()
    const [x, y] = proj(lon, lat)
    const g = new THREE.Group()
    const col = total > 0 ? 0x10ff9a : 0xf87171
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 6, 12).translate(0, 3, 0),
      new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.85 }))
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glowTex, color: col, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }))
    glow.scale.setScalar(4)
    g.add(beam, glow)
    g.position.set(x, 0.6, -y)
    g.userData.pulse = true
    this.lookupMarker = g
    this.europe.add(g)
    this.flyTo(new THREE.Vector3(x, 12, -y + 10), new THREE.Vector3(x, 0, -y))
  }

  private highlightCountries() {
    for (const m of this.countryMeshes) {
      const mat = m.material as THREE.MeshStandardMaterial
      const sel = this.selectedCountry && m.userData.cc === this.selectedCountry
      const dim = this.selectedCountry && !sel
      mat.color.setHex(sel ? 0x10b981 : m.userData.baseColor)
      mat.emissive.setHex(sel ? 0x0b5e45 : m.userData.covered ? 0x062a22 : 0)
      mat.opacity = dim ? 0.55 : 1
      mat.transparent = !!dim
    }
  }

  // ---------------------------------------------------------------- city
  async enterCity(stat: { id: string; lat: number; lon: number }, points: Point[], buildings: any | null) {
    this.mode = 'city'
    this.cityOrigin = { lat: stat.lat, lon: stat.lon }
    this.europe.visible = false
    this.city.visible = true
    this.scene.fog = new THREE.FogExp2(0x050913, 0.0028)
    this.controls.maxDistance = 900
    this.clearCity()

    const ground = new THREE.Mesh(new THREE.CircleGeometry(900, 64), new THREE.MeshStandardMaterial({ color: 0x0a1424, roughness: 1 }))
    ground.rotation.x = -Math.PI / 2
    this.city.add(ground)
    const grid = new THREE.GridHelper(1800, 180, 0x123049, 0x0d2033)
    grid.position.y = 0.02
    this.city.add(grid)

    if (buildings?.buildings?.length) {
      const geoms: THREE.BufferGeometry[] = []
      for (const b of buildings.buildings as { h: number; c: [number, number][] }[]) {
        const pts = b.c.map(([lon, lat]) => new THREE.Vector2(...this.local(lon, lat)))
        if (pts.length < 4) continue
        const h = (b.h || 9 + ((pts.length * 7) % 13)) / CITY_SCALE
        try {
          const g = new THREE.ExtrudeGeometry(new THREE.Shape(pts), { depth: h, bevelEnabled: false })
          g.deleteAttribute('uv')
          geoms.push(g)
        } catch { /* degenerate footprint */ }
      }
      if (geoms.length) {
        const merged = mergeGeometries(geoms, false)
        geoms.forEach((g) => g.dispose())
        if (merged) {
          const mesh = new THREE.Mesh(merged, new THREE.MeshStandardMaterial({
            color: 0x64748b, roughness: 0.55, metalness: 0.25, emissive: 0x16233a,
          }))
          mesh.rotation.x = -Math.PI / 2
          this.city.add(mesh)
          const edges = new THREE.LineSegments(new THREE.EdgesGeometry(merged, 30),
            new THREE.LineBasicMaterial({ color: 0x5eead4, transparent: true, opacity: 0.22 }))
          edges.rotation.x = -Math.PI / 2
          this.city.add(edges)
        }
      }
    }

    this.cityPoints = points
    const pin = new THREE.CylinderGeometry(0.9, 0.25, 1, 8).translate(0, 0.5, 0)
    const inst = new THREE.InstancedMesh(pin, new THREE.MeshBasicMaterial({ color: 0xffffff }), points.length)
    const color = new THREE.Color()
    points.forEach((p, i) => {
      color.setHex(VEG_COLORS[p[4]])
      inst.setColorAt(i, color)
    })
    this.cityPins = inst
    this.applyPinFilter()
    this.city.add(inst)

    // halo sprites for veg-tagged places make them pop at night
    const vegPts = points.filter((p) => p[4] >= 2)
    const halo = new THREE.BufferGeometry()
    halo.setAttribute('position', new THREE.Float32BufferAttribute(vegPts.flatMap((p) => {
      const [x, y] = this.local(p[3], p[2])
      return [x, 9, -y]
    }), 3))
    const haloMat = new THREE.PointsMaterial({ size: 22, map: this.glowTex, color: 0x10ff9a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })
    const haloPts = new THREE.Points(halo, haloMat)
    haloPts.userData.halo = true
    this.city.add(haloPts)

    this.refreshLabels()
    this.camera.position.set(0, 600, 500)
    this.controls.target.set(0, 0, 0)
    this.flyTo(new THREE.Vector3(60, 150, 190), new THREE.Vector3(0, 0, 0))
  }

  applyPinFilter() {
    if (!this.cityPins) return
    const m = new THREE.Matrix4()
    this.cityPoints.forEach((p, i) => {
      const [x, y] = this.local(p[3], p[2])
      const visible = !this.vegOnly || p[4] >= 1
      const h = visible ? [3, 4, 7, 9][p[4]] : 0.0001
      m.makeScale(visible ? 1 : 0.0001, h, visible ? 1 : 0.0001)
      m.setPosition(x, 0, -y)
      this.cityPins!.setMatrixAt(i, m)
    })
    this.cityPins.instanceMatrix.needsUpdate = true
    this.cityPins.computeBoundingSphere()
    this.city.children.forEach((c) => { if (c.userData.halo) c.visible = true })
  }

  exitCity() {
    this.clearCity()
    this.mode = 'europe'
    this.city.visible = false
    this.europe.visible = true
    this.scene.fog = new THREE.FogExp2(0x050913, 0.0045)
    this.controls.maxDistance = 220
  }

  private clearCity() {
    for (const c of [...this.city.children]) {
      this.city.remove(c)
      const anyC = c as any
      anyC.geometry?.dispose?.()
      anyC.material?.dispose?.()
    }
    this.cityPins = null
    this.cityPoints = []
  }

  private local(lon: number, lat: number): [number, number] {
    const x = ((lon - this.cityOrigin.lon) * 111320 * Math.cos((this.cityOrigin.lat * Math.PI) / 180)) / CITY_SCALE
    const y = ((lat - this.cityOrigin.lat) * 110540) / CITY_SCALE
    return [x, y]
  }

  // ---------------------------------------------------------------- labels
  private refreshLabels() {
    this.labelsEl.innerHTML = ''
    this.labels = []
    if (this.mode !== 'europe') return
    for (const b of this.beacons) {
      if (!b.mesh.visible) continue
      if (!this.selectedCountry && b.stat.total < 2500) continue
      const el = document.createElement('div')
      el.textContent = `${b.stat.name} · ${(this.vegOnly ? b.stat.veg_tagged : b.stat.total).toLocaleString()}`
      Object.assign(el.style, {
        position: 'absolute', fontSize: '11px', fontWeight: '700', color: '#d1fae5', whiteSpace: 'nowrap',
        textShadow: '0 1px 6px #000', transform: 'translate(-50%, -130%)', pointerEvents: 'none',
      })
      this.labelsEl.appendChild(el)
      this.labels.push({ el, pos: b.mesh.position.clone().setY(b.mesh.scale.y + 0.8) })
    }
  }

  private updateLabels() {
    const w = this.host.clientWidth
    const h = this.host.clientHeight
    const v = new THREE.Vector3()
    for (const l of this.labels) {
      v.copy(l.pos).project(this.camera)
      const hidden = v.z > 1 || Math.abs(v.x) > 1.1 || Math.abs(v.y) > 1.1
      l.el.style.display = hidden ? 'none' : 'block'
      l.el.style.left = `${((v.x + 1) / 2) * w}px`
      l.el.style.top = `${((1 - v.y) / 2) * h}px`
    }
  }

  // ---------------------------------------------------------------- interaction
  private onMove = (e: PointerEvent) => {
    const r = this.renderer.domElement.getBoundingClientRect()
    this.mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1)
    this.mousePx = { x: e.clientX - r.left, y: e.clientY - r.top }
  }

  private pick(): Hover & { kind?: string; id?: string } | null {
    this.raycaster.setFromCamera(this.mouse, this.camera)
    if (this.mode === 'europe') {
      const hits = this.raycaster.intersectObjects([...this.beacons.filter((b) => b.mesh.visible).map((b) => b.mesh), ...this.countryMeshes], false)
      const hit = hits[0]
      if (this.hoveredCountry && this.hoveredCountry.userData.cc !== this.selectedCountry) {
        (this.hoveredCountry.material as THREE.MeshStandardMaterial).emissive.setHex(this.hoveredCountry.userData.covered ? 0x062a22 : 0)
      }
      this.hoveredCountry = null
      if (!hit) return null
      if (hit.object.userData.city) {
        const s: CityStat = hit.object.userData.city
        return { kind: 'city', id: s.id, ...this.mousePx, title: `${s.name}, ${s.country}`, lines: [
          `${s.total.toLocaleString()} restaurants & cafés`, `${s.veg_tagged} tagged vegetarian/vegan`, `${s.breakfast} breakfast spots`, 'Click to explore in 3D'] }
      }
      const m = hit.object as THREE.Mesh
      this.hoveredCountry = m
      if (m.userData.cc !== this.selectedCountry) (m.material as THREE.MeshStandardMaterial).emissive.setHex(0x1e3a5f)
      const cities = this.beacons.filter((b) => b.stat.country_code === m.userData.cc)
      const total = cities.reduce((s, b) => s + b.stat.total, 0)
      return { kind: 'country', id: m.userData.cc, ...this.mousePx, title: m.userData.name, lines: m.userData.covered
        ? [`${cities.length} cities covered`, `${total.toLocaleString()} places`, 'Click to zoom in']
        : ['Not covered yet'] }
    }
    if (this.cityPins) {
      const hit = this.raycaster.intersectObject(this.cityPins, false)[0]
      if (hit && hit.instanceId != null) {
        const p = this.cityPoints[hit.instanceId]
        const veg = ['no veg tag', 'veg-friendly cuisine', 'vegetarian options', '100% vegetarian/vegan'][p[4]]
        return { kind: 'pin', id: p[0], ...this.mousePx, title: p[1], lines: [`${p[5]}${p[6] ? ' · ' + p[6] : ''}`, veg] }
      }
    }
    return null
  }

  private onClick = () => {
    const h = this.pick()
    if (!h) return
    if (h.kind === 'city' && h.id) this.onPickCity(h.id)
    if (h.kind === 'country' && h.id && this.covered.has(h.id)) this.onPickCountry(h.id)
  }

  private flyTo(pos: THREE.Vector3, target: THREE.Vector3) {
    this.camGoal = { pos, target }
  }

  zoom(f: number) {
    const dir = this.camera.position.clone().sub(this.controls.target)
    this.camGoal = { pos: this.controls.target.clone().add(dir.multiplyScalar(f)), target: this.controls.target.clone() }
  }

  private resize = () => {
    const w = this.host.clientWidth
    const h = this.host.clientHeight
    this.renderer.setSize(w, h)
    this.camera.aspect = w / Math.max(h, 1)
    this.camera.updateProjectionMatrix()
  }

  private loop = () => {
    this.raf = requestAnimationFrame(this.loop)
    const t = this.clock.getElapsedTime()
    if (this.camGoal) {
      this.camera.position.lerp(this.camGoal.pos, 0.07)
      this.controls.target.lerp(this.camGoal.target, 0.07)
      if (this.camera.position.distanceTo(this.camGoal.pos) < 0.05) this.camGoal = null
    }
    this.controls.update()
    for (const [i, b] of this.beacons.entries()) {
      const s = 2.2 + Math.sin(t * 2.2 + i) * 0.5
      b.glow.scale.setScalar(s)
      b.glow.position.y = 0.6 + b.mesh.scale.y
    }
    if (this.lookupMarker) this.lookupMarker.children[1].scale.setScalar(3.5 + Math.sin(t * 4) * 1.2)
    const h = this.pick()
    const key = h ? `${h.title}|${h.x}|${h.y}|${h.lines.join()}` : ''
    if (key !== this.lastHoverKey) {
      this.lastHoverKey = key
      this.onHover(h ? { x: h.x, y: h.y, title: h.title, lines: h.lines } : null)
    }
    this.renderer.domElement.style.cursor = h && h.kind !== 'pin' ? 'pointer' : ''
    this.updateLabels()
    this.renderer.render(this.scene, this.camera)
  }

  dispose() {
    cancelAnimationFrame(this.raf)
    window.removeEventListener('resize', this.resize)
    this.controls.dispose()
    this.renderer.dispose()
    this.host.innerHTML = ''
  }
}
