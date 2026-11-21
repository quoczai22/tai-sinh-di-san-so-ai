// app.js — ĐIỂM KHỞI ĐỘNG của web_ui (index.html nạp file này). Thứ tự:
//   1. áp mức chuyển động đã lưu + đo máy yếu (core/motion)
//   2. data.init(): hỏi /health để chọn chế độ live (có GPU) hay demo (dữ liệu thật đã sinh sẵn)
//   3. startRouter(): vẽ trang theo hash; mọi trang sau đó do core/router.js điều phối.
// Sơ đồ đầy đủ: docs/UI_ARCHITECTURE.md.
import * as data from './core/data.js';
import { pendingGeneration } from './core/generation.js';
import { applyMotionClass, detectSlowMotion } from './core/motion.js';
import { startRouter } from './core/router.js';

applyMotionClass();
detectSlowMotion();
(async () => {
    const pending = pendingGeneration();
    if (pending) location.hash = `#/studio/${encodeURIComponent(pending.heritageId)}`;
    startRouter(await data.init());
})();
