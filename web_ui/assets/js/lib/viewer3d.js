// ---------------------------------------------------------------------------------------------
// Khung xem 3D cho một hiện vật: kéo chuột để xoay 360 độ, lăn chuột để thu phóng, tự xoay nhẹ khi chưa chạm.
// Mô hình là file GLB nhẹ trong assets/models/<mã hiện vật>.glb (tạo bằng scripts/16_export_heritage_glb.py).
// Three.js chỉ tải khi cần. Lỗi hoặc không có WebGL thì giữ nguyên ảnh phẳng.
// Hai cách dùng:
//  · mountViewer(box, id)                  trang riêng của hiện vật: kéo chuột để xoay, tự xoay nhẹ.
//  · hoverSpin(card, box, id)              trang có cả 6 hiện vật: bình hiện sẵn dạng 3D đứng yên, rê chuột vào
//                                          thẻ thì bình tự xoay, rê ra thì đứng yên đúng tại góc đang xoay.
// ---------------------------------------------------------------------------------------------
const MODEL_DIR = './assets/models/';
const MODEL_VERSION = 'finals-69';       // đổi cùng số phiên bản trong index.html để trình duyệt không dùng file GLB cũ
const AUTO_ROTATE_SPEED = 1.4;      // độ/giây nhân với 6, theo OrbitControls
const RESUME_AFTER_MS = 3500;       // sau khi thả chuột bao lâu thì tự xoay lại
const live = new Set();             // các khung đang tồn tại, để dọn khung của trang đã bị gỡ
const reducedMotion = () => document.documentElement.classList.contains('motion-off');

// Quầng bóng mờ dưới chân bình: ảnh gradient tròn vẽ bằng canvas
function shadowTexture(THREE) {
    const c = document.createElement('canvas');
    c.width = c.height = 128;
    const g = c.getContext('2d');
    const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, 'rgba(40,28,10,.5)');
    grad.addColorStop(1, 'rgba(40,28,10,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
}

/**
 * Gắn khung xem 3D vào `box` (phần tử đang chứa ảnh phẳng của hiện vật).
 * hover = true: chế độ thẻ trong lưới, không kéo chuột được, chỉ xoay khi gọi spin(true).
 * Trả về { spin(bật/tắt) } khi dựng xong, false khi phải giữ ảnh phẳng.
 */
export async function mountViewer(box, heritageId, { hover = false } = {}) {
    for (const v of live) if (!v.box.isConnected) v.stop();         // dọn khung của trang đã gỡ
    let THREE, GLTFLoader, OrbitControls, RoomEnvironment;
    try {
        [THREE, { GLTFLoader }, { OrbitControls }, { RoomEnvironment }] = await Promise.all([
            import('three'),
            import('../vendor/three/loaders/GLTFLoader.js'),
            import('../vendor/three/controls/OrbitControls.js'),
            import('../vendor/three/environments/RoomEnvironment.js'),
        ]);
    } catch { return false; }

    let renderer;
    try {
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch { return false; }                                       // máy không hỗ trợ WebGL

    let gltf;
    try {
        gltf = await new GLTFLoader().loadAsync(`${MODEL_DIR}${encodeURIComponent(heritageId)}.glb?v=${MODEL_VERSION}`);
    } catch { renderer.dispose(); return false; }                   // chưa có mô hình cho hiện vật này
    // Trang có thể gắn khung vào cây DOM chậm hơn lúc tải xong mô hình: chờ tối đa 5 giây
    for (let i = 0; i < 50 && !box.isConnected; i++) await new Promise((r) => setTimeout(r, 100));
    if (!box.isConnected) { renderer.dispose(); return false; }     // người xem đã chuyển trang trong lúc tải

    // --- Cảnh: nền trong suốt để khung be của trang hiện ra phía sau ---
    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;   // ánh sáng phản chiếu cho lớp men
    const sun = new THREE.DirectionalLight(0xffffff, 1.1);
    sun.position.set(2, 3, 2.5);
    scene.add(sun);

    const model = gltf.scene;                                       // đã chuẩn hoá: chân y = 0, tâm ở gốc, cao 1
    scene.add(model);
    const size = new THREE.Box3().setFromObject(model);
    const radius = Math.max(Math.hypot(size.max.x, size.max.z), Math.hypot(size.min.x, size.min.z));   // bán kính quay quanh trục đứng

    const shadow = new THREE.Mesh(
        new THREE.PlaneGeometry(radius * 2.5, radius * 2.5),
        new THREE.MeshBasicMaterial({ map: shadowTexture(THREE), transparent: true, depthWrite: false }));
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = -0.002;
    scene.add(shadow);

    const camera = new THREE.PerspectiveCamera(28, 1, 0.05, 50);
    const target = new THREE.Vector3(0, 0.5, 0);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(target);
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.autoRotate = !hover && !reducedMotion();
    controls.autoRotateSpeed = AUTO_ROTATE_SPEED;
    controls.minPolarAngle = Math.PI * 0.18;                        // không lật bình quá trên đỉnh hoặc xuống dưới đáy
    controls.maxPolarAngle = Math.PI * 0.62;
    controls.enabled = !hover;                                      // thẻ trong lưới chỉ xoay khi rê chuột, không kéo được

    // Đặt khung hình vừa cả chiều cao lẫn bề ngang của bình
    const fit = () => {
        const w = box.clientWidth, h = box.clientHeight;
        if (!w || !h) return;
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
        const d = Math.max(0.5 / t, radius / (t * camera.aspect)) * (hover ? 1.12 : 1.35);   // thẻ trong lưới: bình to gần bằng ảnh phẳng
        controls.minDistance = d * 0.55;
        controls.maxDistance = d * 1.6;
        if (!fit.done) {
            camera.position.set(0, 0.55 + d * 0.12, d);             // nhìn hơi từ trên xuống
            fit.done = true;
        }
        camera.updateProjectionMatrix();
        if (hover && !raf) draw();                                  // đổi kích thước làm canvas trống: vẽ lại đúng góc đang đứng
    };

    const canvas = renderer.domElement;
    canvas.className = 'viewer3d';
    canvas.setAttribute('aria-label', 'Mô hình 3D của hiện vật, kéo chuột để xoay');
    if (hover) canvas.style.touchAction = 'auto';                    // không chặn cuộn trang bằng ngón tay trên thẻ
    box.append(canvas);
    let raf = 0;
    const draw = () => { controls.update(); renderer.render(scene, camera); };
    const ro = new ResizeObserver(fit);
    ro.observe(box);
    fit();

    // Dừng tự xoay khi đang kéo, xoay lại sau khi thả vài giây
    let resume;
    controls.addEventListener('start', () => { clearTimeout(resume); controls.autoRotate = false; });
    controls.addEventListener('end', () => { resume = setTimeout(() => { controls.autoRotate = !reducedMotion(); }, RESUME_AFTER_MS); });

    // Vòng vẽ chỉ chạy khi cần; tự dọn khi khung xem bị gỡ khỏi trang
    const entry = { box, stop() {
        if (entry.dead) return;
        entry.dead = true;
        cancelAnimationFrame(raf);
        ro.disconnect();
        clearTimeout(resume);
        controls.dispose();
        renderer.dispose();
        pmrem.dispose();
        live.delete(entry);
    } };
    live.add(entry);
    const frame = () => {
        if (!box.isConnected) { entry.stop(); return; }
        draw();
        raf = requestAnimationFrame(frame);
    };
    const run = () => { if (!raf && !entry.dead) raf = requestAnimationFrame(frame); };
    const halt = () => { cancelAnimationFrame(raf); raf = 0; };

    box.classList.add('has-3d');
    if (hover) draw();                                              // vẽ khung đầu tiên rồi đứng yên
    else run();
    return {
        spin(on) {
            controls.autoRotate = on;
            if (on) run(); else halt();                             // dừng vòng vẽ: canvas giữ nguyên hình cuối
        },
    };
}

/**
 * Thẻ trong lưới nhiều hiện vật: bình hiện sẵn dạng 3D đứng yên (dựng khi thẻ sắp vào màn hình).
 * Rê chuột (hoặc focus bàn phím) vào thẻ thì bình tự xoay như ở trang riêng, rê ra thì đứng yên tại góc đang xoay.
 * Trong lúc chờ dựng 3D, thẻ vẫn hiện ảnh phẳng.
 */
export function hoverSpin(card, box, heritageId) {
    let view = null, loading = false, failed = false, hovering = false;
    const load = async () => {
        if (view || loading || failed) return;
        loading = true;
        view = await mountViewer(box, heritageId, { hover: true });
        loading = false;
        failed = !view;
        if (view && hovering && !reducedMotion()) view.spin(true);   // người xem đã rê chuột vào trong lúc tải
    };
    new IntersectionObserver((entries, obs) => {
        if (entries.some((e) => e.isIntersecting)) { obs.disconnect(); load(); }
    }, { rootMargin: '200px' }).observe(card);
    const enter = () => { hovering = true; if (reducedMotion()) return; if (view) view.spin(true); else load(); };
    const leave = () => { hovering = false; view?.spin(false); };
    card.addEventListener('pointerenter', enter);
    card.addEventListener('pointerleave', leave);
    card.addEventListener('focusin', enter);
    card.addEventListener('focusout', leave);
}
