// ---------------------------------------------------------------------------------------------
// Khung xem 3D cho một hiện vật: kéo chuột để xoay 360 độ, lăn chuột để thu phóng, tự xoay nhẹ khi chưa chạm.
// Mô hình là file GLB nhẹ trong assets/models/<mã hiện vật>.glb (tạo bằng scripts/16_export_heritage_glb.py).
// Three.js chỉ tải khi mở trang Studio của một hiện vật. Lỗi hoặc không có WebGL thì giữ nguyên ảnh phẳng.
// ---------------------------------------------------------------------------------------------
const MODEL_DIR = './assets/models/';
const MODEL_VERSION = 'finals-59';       // đổi cùng số phiên bản trong index.html để trình duyệt không dùng file GLB cũ
const AUTO_ROTATE_SPEED = 1.4;      // độ/giây nhân với 6, theo OrbitControls
const RESUME_AFTER_MS = 3500;       // sau khi thả chuột bao lâu thì tự xoay lại

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
 * Trả về true khi dựng xong, false khi phải giữ ảnh phẳng.
 */
export async function mountViewer(box, heritageId) {
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
    controls.autoRotate = true;
    controls.autoRotateSpeed = AUTO_ROTATE_SPEED;
    controls.minPolarAngle = Math.PI * 0.18;                        // không lật bình quá trên đỉnh hoặc xuống dưới đáy
    controls.maxPolarAngle = Math.PI * 0.62;

    // Đặt khung hình vừa cả chiều cao lẫn bề ngang của bình
    const fit = () => {
        const w = box.clientWidth, h = box.clientHeight;
        if (!w || !h) return;
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
        const d = Math.max(0.5 / t, radius / (t * camera.aspect)) * 1.35;
        controls.minDistance = d * 0.55;
        controls.maxDistance = d * 1.6;
        if (!fit.done) {
            camera.position.set(0, 0.55 + d * 0.12, d);             // nhìn hơi từ trên xuống
            fit.done = true;
        }
        camera.updateProjectionMatrix();
    };

    const canvas = renderer.domElement;
    canvas.className = 'viewer3d';
    canvas.setAttribute('aria-label', 'Mô hình 3D của hiện vật, kéo chuột để xoay');
    box.append(canvas);
    const ro = new ResizeObserver(fit);
    ro.observe(box);
    fit();

    // Dừng tự xoay khi đang kéo, xoay lại sau khi thả vài giây
    let resume;
    controls.addEventListener('start', () => { clearTimeout(resume); controls.autoRotate = false; });
    controls.addEventListener('end', () => { resume = setTimeout(() => { controls.autoRotate = true; }, RESUME_AFTER_MS); });

    // Vòng vẽ: tự dừng và dọn dẹp khi khung xem bị gỡ khỏi trang
    const stop = () => {
        ro.disconnect();
        clearTimeout(resume);
        controls.dispose();
        renderer.dispose();
        pmrem.dispose();
    };
    const loop = () => {
        if (!box.isConnected) { stop(); return; }
        controls.update();
        renderer.render(scene, camera);
        requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
    box.classList.add('has-3d');
    return true;
}
