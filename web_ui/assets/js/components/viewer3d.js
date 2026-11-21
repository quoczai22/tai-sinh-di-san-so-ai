// components/viewer3d.js — KHUNG XEM HIỆN VẬT 3D (Three.js, tải lười): Studio xoay 360° bằng chuột, thẻ hiện vật xoay khi rê chuột.
// Dùng chung một renderer, dựng lần lượt từng khung (hàng đợi) để không giật; lỗi WebGL thì giữ ảnh phẳng.
// Ra: mountViewer(box, mã) → { spin, toggleSpin, setZoom } | false; hoverSpin(thẻ, box, mã). Mô hình: assets/models/<mã>.glb.
const MODEL_DIR = './assets/models/';
const MODEL_VERSION = 'finals-80';
const AUTO_ROTATE_SPEED = 1.4;
const RESUME_AFTER_MS = 3500;
const live = new Set(), models = new Map(), queue = [];
let modules, shared, draining = false;
const reducedMotion = () => document.documentElement.classList.contains('motion-off');
const yieldToBrowser = () => new Promise(resolve => {
    if (window.requestIdleCallback) requestIdleCallback(resolve, { timeout: 250 });
    else setTimeout(resolve, 32);
});
function dependencies() {
    return modules ||= Promise.all([
        import('three'), import('../vendor/three/loaders/GLTFLoader.js'),
        import('../vendor/three/controls/OrbitControls.js'),
        import('../vendor/three/environments/RoomEnvironment.js'),
    ]).then(([THREE, { GLTFLoader }, { OrbitControls }, { RoomEnvironment }]) =>
        ({ THREE, GLTFLoader, OrbitControls, RoomEnvironment }));
}
function modelFor(id, GLTFLoader) {
    if (!models.has(id)) models.set(id, new GLTFLoader()
        .loadAsync(`${MODEL_DIR}${encodeURIComponent(id)}.glb?v=${MODEL_VERSION}`)
        .catch(error => { models.delete(id); throw error; }));
    return models.get(id);
}
function shadowTexture(THREE) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 256;
    const g = canvas.getContext('2d');
    const gradient = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gradient.addColorStop(0, 'rgba(40,28,10,.55)');
    gradient.addColorStop(0.28, 'rgba(40,28,10,.30)');
    gradient.addColorStop(0.65, 'rgba(40,28,10,.08)');
    gradient.addColorStop(1, 'rgba(40,28,10,0)');
    g.fillStyle = gradient;
    g.fillRect(0, 0, 256, 256);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
}
function makeEnvironment(renderer, THREE, RoomEnvironment) {
    const pmrem = new THREE.PMREMGenerator(renderer);
    const room = new RoomEnvironment();
    const target = pmrem.fromScene(room, 0.04);
    room.dispose();
    pmrem.dispose();
    return target;
}
function cleanupDetached() {
    for (const entry of live) if (!entry.box.isConnected) entry.stop();
}
if (typeof MutationObserver !== 'undefined') {
    new MutationObserver(cleanupDetached).observe(document.documentElement, { childList: true, subtree: true });
}
function sharedRenderer({ THREE, RoomEnvironment }) {
    if (!shared) {
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        try { shared = { renderer, env: makeEnvironment(renderer, THREE, RoomEnvironment) }; }
        catch (error) { renderer.dispose(); renderer.forceContextLoss(); throw error; }
    }
    return shared;
}
function makeScene(gltf, THREE, env) {
    const scene = new THREE.Scene();
    scene.environment = env.texture;
    const sun = new THREE.DirectionalLight(0xffffff, 1.1);
    sun.position.set(2, 3, 2.5);
    scene.add(sun);
    // The cached GLTF owns geometry and materials. Each viewer owns only its object hierarchy.
    const model = gltf.scene.clone(true);
    scene.add(model);
    const size = new THREE.Box3().setFromObject(model);
    const radius = Math.max(Math.hypot(size.max.x, size.max.z), Math.hypot(size.min.x, size.min.z));
    const shadow = new THREE.Mesh(new THREE.PlaneGeometry(radius * 2.5, radius * 2.5),
        new THREE.MeshBasicMaterial({ map: shadowTexture(THREE), transparent: true, depthWrite: false }));
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = -0.002;
    scene.add(shadow);
    return {
        scene, model, radius, dispose() {
            shadow.geometry.dispose(); shadow.material.map.dispose(); shadow.material.dispose();
        }
    };
}
async function build(box, id, hover) {
    cleanupDetached();
    let deps, gltf;
    try {
        deps = await dependencies();
        gltf = await modelFor(id, deps.GLTFLoader);
    } catch { return false; }
    for (let i = 0; i < 50 && !box.isConnected; i++) await new Promise(r => setTimeout(r, 100));
    if (!box.isConnected) return false;
    const { THREE, OrbitControls, RoomEnvironment } = deps;
    let renderer, env, own = false, data, controls, canvas, ro, io, entry;
    try {
        if (hover) ({ renderer, env } = sharedRenderer(deps));
        else {
            for (const existing of live) if (!existing.hover) existing.stop();
            renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            own = true;
            env = makeEnvironment(renderer, THREE, RoomEnvironment);
        }
        data = makeScene(gltf, THREE, env);
        const { scene, model, radius } = data;
        const camera = new THREE.PerspectiveCamera(28, 1, 0.05, 50);
        canvas = hover ? document.createElement('canvas') : renderer.domElement;
        const ctx = hover ? canvas.getContext('2d') : null;
        if (hover && !ctx) throw new Error('2D canvas unavailable');
        canvas.className = 'viewer3d';
        canvas.setAttribute('aria-label', 'Mô hình 3D của hiện vật, kéo chuột để xoay');
        if (hover) canvas.style.touchAction = 'auto';
        let autoRotateActive = !reducedMotion();
        controls = hover ? null : new OrbitControls(camera, canvas);
        if (controls) {
            controls.target.set(0, 0.46, 0);
            controls.enablePan = false;
            controls.enableZoom = false;
            controls.enableDamping = true;
            controls.dampingFactor = 0.08;
            controls.autoRotate = autoRotateActive;
            controls.autoRotateSpeed = AUTO_ROTATE_SPEED;
            controls.minPolarAngle = Math.PI * 0.18;
            controls.maxPolarAngle = Math.PI * 0.62;
        }
        let raf = 0, last = 0, visible = true, spinning = false, resume;
        const draw = (delta = 0) => {
            if (hover) {
                if (spinning && !reducedMotion()) model.rotation.y += 2 * Math.PI / 60 * AUTO_ROTATE_SPEED * delta;
                if (renderer.domElement.width !== canvas.width || renderer.domElement.height !== canvas.height) {
                    renderer.setPixelRatio(1);
                    renderer.setSize(canvas.width, canvas.height, false);
                }
            } else controls.update(delta);
            renderer.render(scene, camera);
            if (hover) {
                // Renderer nền trong suốt: phải xoá khung cũ, nếu không bình xoay để lại vệt chồng hình
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(renderer.domElement, 0, 0, canvas.width, canvas.height);
            }
        };
        const fit = () => {
            const w = box.clientWidth, h = box.clientHeight;
            if (!w || !h) return;
            const ratio = Math.min(window.devicePixelRatio || 1, hover ? 1.5 : 2);
            if (hover) {
                canvas.width = Math.max(1, Math.round(w * ratio));
                canvas.height = Math.max(1, Math.round(h * ratio));
                renderer.setPixelRatio(1);
                renderer.setSize(canvas.width, canvas.height, false);
            } else {
                renderer.setPixelRatio(ratio);
                renderer.setSize(w, h, false);
            }
            camera.aspect = w / h;
            const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
            const d = Math.max(0.5 / t, radius / (t * camera.aspect)) * (hover ? 1.25 : 1.35);
            if (controls) { controls.minDistance = d * 0.55; controls.maxDistance = d * 1.6; }
            if (!fit.done) { camera.position.set(0, 0.5 + d * 0.08, d); fit.done = true; }
            if (hover) camera.lookAt(0, 0.46, 0);
            camera.updateProjectionMatrix();
            if (hover && !raf) draw();
        };
        const halt = () => { cancelAnimationFrame(raf); raf = 0; last = 0; };
        const frame = time => {
            raf = 0;
            if (!box.isConnected) { entry.stop(); return; }
            if (!visible || document.hidden || (hover && (!spinning || reducedMotion()))) return;
            const delta = last ? Math.min((time - last) / 1000, 0.1) : 0;
            last = time;
            draw(delta);
            raf = requestAnimationFrame(frame);
        };
        const run = () => { if (!raf && visible && !document.hidden && !entry.dead) { last = 0; raf = requestAnimationFrame(frame); } };
        const onVisibility = () => { if (document.hidden) halt(); else if (!hover || spinning) run(); };
        entry = {
            box, hover, dead: false, stop() {
                if (entry.dead) return;
                entry.dead = true;
                halt();
                io?.disconnect(); ro?.disconnect();
                document.removeEventListener('visibilitychange', onVisibility);
                clearTimeout(resume);
                controls?.dispose(); data?.dispose();
                canvas?.remove();
                box.classList.remove('has-3d');
                if (own) { env?.dispose(); renderer.dispose(); renderer.forceContextLoss(); }
                live.delete(entry);
            }
        };
        if (controls) {
            controls.addEventListener('start', () => { clearTimeout(resume); controls.autoRotate = false; });
            controls.addEventListener('end', () => {
                if (autoRotateActive) {
                    resume = setTimeout(() => { controls.autoRotate = !reducedMotion() && autoRotateActive; }, RESUME_AFTER_MS);
                }
            });
        }
        if (renderer.compileAsync) await renderer.compileAsync(scene, camera);
        if (!box.isConnected) { entry.stop(); return false; }
        box.append(canvas);
        live.add(entry);
        ro = new ResizeObserver(fit); ro.observe(box);
        io = new IntersectionObserver(entries => {
            visible = entries.some(e => e.isIntersecting);
            if (visible) { if (!hover || spinning) run(); } else halt();
        }); io.observe(box);
        document.addEventListener('visibilitychange', onVisibility);
        fit();
        if (hover) draw(); else run();
        box.classList.add('has-3d');

        const setZoom = (factor) => {
            const z = Math.max(0.7, Math.min(1.8, Number(factor) || 1));
            camera.zoom = z;
            camera.updateProjectionMatrix();
            if (!raf && visible) draw();
            return z;
        };

        const toggleSpin = (force) => {
            autoRotateActive = typeof force === 'boolean' ? force : !autoRotateActive;
            if (controls) {
                controls.autoRotate = autoRotateActive && !reducedMotion();
                if (autoRotateActive) run();
            } else {
                spinning = autoRotateActive && !reducedMotion();
                if (spinning) run(); else halt();
            }
            return autoRotateActive;
        };

        return {
            spin(on) { spinning = on && !reducedMotion(); if (spinning) run(); else halt(); },
            stop: entry.stop,
            setZoom,
            toggleSpin,
            isSpinning() { return autoRotateActive; }
        };
    } catch {
        if (entry) entry.stop();
        else {
            controls?.dispose(); data?.dispose();
            if (own && renderer) { env?.dispose(); renderer.dispose(); renderer.forceContextLoss(); }
        }
        return false;
    }
}
async function drainQueue() {
    if (draining) return;
    draining = true;
    while (queue.length) {
        await yieldToBrowser();
        const { box, id, resolve } = queue.shift();
        resolve(box.isConnected ? await build(box, id, true) : false);
    }
    draining = false;
}
export function mountViewer(box, heritageId, { hover = false } = {}) {
    if (!hover) return build(box, heritageId, false);
    return new Promise(resolve => { queue.push({ box, id: heritageId, resolve }); drainQueue(); });
}
export function hoverSpin(card, box, heritageId) {
    let view = null, loading = false, failed = false, hovering = false;
    const load = async () => {
        if (view || loading || failed) return;
        loading = true;
        view = await mountViewer(box, heritageId, { hover: true });
        loading = false;
        failed = !view;
        if (view && hovering && !reducedMotion()) view.spin(true);
    };
    new IntersectionObserver((entries, observer) => {
        if (entries.some(e => e.isIntersecting)) { observer.disconnect(); load(); }
    }, { rootMargin: '200px' }).observe(card);
    const enter = () => { hovering = true; if (reducedMotion()) return; if (view) view.spin(true); else load(); };
    const leave = () => { hovering = false; view?.spin(false); };
    card.addEventListener('pointerenter', enter);
    card.addEventListener('pointerleave', leave);
    card.addEventListener('focusin', enter);
    card.addEventListener('focusout', leave);
}
