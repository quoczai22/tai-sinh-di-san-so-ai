# -*- coding: utf-8 -*-
"""Mô hình BPMN AS-IS (hiện trạng theo mã nguồn, 24/11/2026) và TO-BE (đề xuất tối ưu) của Tái Sinh Di Sản Số.

Quy ước: mỗi hàm trả về một Diagram. step là vị trí dọc (thứ tự thời gian), row là cột phụ trong lane.
Mọi phần tử AS-IS có căn cứ trong mã (bảng "Căn cứ" trong docs/business-analysis/02_BPMN.md).
Phần tử TO-BE mới (đề xuất) tô màu xanh lá.
"""
from bpmnkit import Diagram

PLATFORM = "Nền tảng Tái Sinh Di Sản Số"
NEW = "new"


# ============================================================================ BP-00 Bản đồ quy trình
def bp00(variant):
    tobe = variant == "TO-BE"
    d = Diagram(f"BP00_{variant.replace('-', '')}", f"BP-00 {variant} — Bản đồ quy trình")
    d.pool("OWN", "Chủ sở hữu ảnh", black_box=True, side="left")
    d.pool("P", PLATFORM, [("L_DATA", "Người quản lý dữ liệu"), ("L_USR", "Nhà thiết kế"),
                           ("L_SYS", "Hệ thống"), ("L_QC", "QC Officer")])
    d.pool("EXP", "Hội đồng chuyên gia", black_box=True)
    N = d.n
    N("S_D", "startEvent", "Có hiện vật mới", "P", "L_DATA", 0)
    N("C4", "callActivity", "BP-04 Tiếp nhận hiện vật, quản lý quyền", "P", "L_DATA", 1)
    N("E_D", "endEvent", "Hiện vật có trên Studio", "P", "L_DATA", 2)
    N("DS_H", "dataStoreReference", "Danh mục hiện vật", "P", "L_SYS", 1, 1, label="below")
    N("S_U", "startEvent", "Cần một thiết kế", "P", "L_USR", 3)
    N("C1", "callActivity", "BP-01 Tạo thiết kế áo dài", "P", "L_SYS", 4)
    N("C2", "callActivity", "BP-02 Xem, tải, chỉnh sửa thiết kế", "P", "L_USR", 5)
    N("E_U", "endEvent", "Kết thúc phiên thiết kế", "P", "L_USR", 6)
    N("DS_P", "dataStoreReference", "Kho Design Passport", "P", "L_SYS", 6, 1, label="below")
    if tobe:
        N("S_Q", "startEvent", "Thiết kế đổi trạng thái duyệt", "P", "L_SYS", 7.2, ev="conditional",
          timer="approval.status thay đổi", color=NEW)
    else:
        N("S_Q", "startEvent", "QC mở đợt thẩm định thủ công", "P", "L_QC", 7.2)
    N("C3", "callActivity", "BP-03 Kiểm soát chất lượng, thẩm định, xuất bản", "P", "L_QC" if not tobe else "L_SYS", 8.2)
    N("E_Q", "endEvent", "Thiết kế có kết luận", "P", "L_QC" if not tobe else "L_SYS", 9.2)
    F = d.f
    F("S_D", "C4"); F("C4", "E_D")
    F("S_U", "C1", exit="bottom", enter="left"); F("C1", "C2", exit="bottom", enter="top"); F("C2", "E_U")
    F("S_Q", "C3", **({} if tobe else {})); F("C3", "E_Q")
    d.d("C4", "DS_H"); d.d("DS_H", "C1", exit="bottom", enter="top")
    d.d("C1", "DS_P", exit="right", enter="top")
    d.d("C2", "DS_P", exit="right", enter="left", via=[lambda D: ("x", D.lx("L_SYS"))])
    if tobe:
        d.d("DS_P", "C3", exit="bottom", enter="right", eoff=-30)
    else:
        d.d("DS_P", "C3", exit="bottom", enter="left")
    d.m("C4", "OWN", "Đề nghị cấp phép")
    d.m("C3", "EXP", "Gói / link chấm mù", offset=4 if tobe else -14)
    d.m("EXP", "C3", "Phiếu chấm", offset=30 if tobe else 14)
    return d


# ============================================================================ BP-01 Tạo thiết kế áo dài
def bp01():
    d = Diagram("BP01", "BP-01 — Tạo thiết kế áo dài (AS-IS, giữ nguyên ở TO-BE)")
    d.pool("P", PLATFORM, [("L_USR", "Nhà thiết kế"), ("L_GW", "Ứng dụng web"),
                           ("L_API", "API và pipeline AI")])
    d.pool("OPS", "Người vận hành", black_box=True)
    N = d.n
    N("S1", "startEvent", "Cần một thiết kế áo dài", "P", "L_USR", 0)
    N("T1", "userTask", "Chọn hiện vật, xem mô hình 3D và sổ hoa văn", "P", "L_USR", 1)
    N("T2", "userTask", "Bấm Tạo thiết kế", "P", "L_USR", 2)
    N("G1", "exclusiveGateway", "Máy GPU sẵn sàng?", "P", "L_GW", 3)
    N("T3", "serviceTask", "Trả bộ thiết kế sinh sẵn", "P", "L_GW", 4, -1)
    N("T4", "serviceTask", "Chuyển yêu cầu sinh tới API", "P", "L_GW", 4)
    N("G2", "exclusiveGateway", "Còn hạn mức?", "P", "L_API", 5, label="belowleft")
    N("T11", "sendTask", "Báo vượt hạn mức, cảnh báo vận hành", "P", "L_API", 6, 1)
    N("E1", "endEvent", "Không tạo được", "P", "L_API", 7, 1, label="below")
    N("T5", "serviceTask", "Xếp hàng chờ GPU", "P", "L_API", 6)
    N("T6", "businessRuleTask", "Kiểm tra quyền mục đích \"thử nghiệm\"", "P", "L_API", 7)
    N("G3", "exclusiveGateway", "Được phép?", "P", "L_API", 8, label="belowleft")
    N("E2", "endEvent", "Hiện vật không được dùng", "P", "L_API", 9, 1, ev="error", error_name="RIGHTS_DENIED", label="below")
    N("T7", "serviceTask", "Chuẩn bị hoa văn", "P", "L_API", 9)
    N("T8", "serviceTask", "Sinh áo dài nền, tách vùng áo", "P", "L_API", 10)
    N("SP", "subProcess", "Tạo 4 phương án", "P", "L_API", 11, multi="sequential")
    N("BE", "boundaryEvent", "Không phương án nào thành công", "P", None, 11, attach="SP", attach_side="bottom",
      ev="error", error_name="ALL_VARIANTS_FAILED", label="right")
    N("T12", "sendTask", "Báo lỗi trên trang, cảnh báo vận hành", "P", "L_GW", 12.0)
    N("E3", "endEvent", "Tạo thiết kế thất bại", "P", "L_GW", 13.0, ev="error", error_name="JOB_FAILED", label="below")
    N("T9", "serviceTask", "Lập Design Passport cho từng phương án", "P", "L_API", 12.6)
    N("T10", "businessRuleTask", "Gán trạng thái duyệt theo kết quả G2, G3", "P", "L_API", 13.6)
    N("DS", "dataStoreReference", "Kho Design Passport", "P", "L_API", 13.6, 1, label="below")
    N("M1", "exclusiveGateway", "", "P", "L_USR", 14.6)
    N("T13", "userTask", "Xem 4 thiết kế ở trang Kết quả", "P", "L_USR", 15.6)
    N("E4", "endEvent", "Bộ thiết kế sẵn sàng", "P", "L_USR", 16.6)
    F = d.f
    F("S1", "T1"); F("T1", "T2"); F("T2", "G1", exit="bottom", enter="top")
    F("G1", "T4", "Có", cond="health.generation_available = true")
    F("G1", "T3", "Không", exit="left", enter="top", cond="health.generation_available = false")
    F("T4", "G2", exit="bottom", enter="left")
    F("G2", "T5", "Trong hạn mức", cond="lượt trong giờ < 6 và hàng chờ < 3")
    F("G2", "T11", "Vượt hạn mức", exit="right", enter="top", cond="lượt trong giờ ≥ 6 hoặc hàng chờ đầy")
    F("T11", "E1")
    F("T5", "T6"); F("T6", "G3")
    F("G3", "T7", "Được phép", cond="rights_gate(experiment).allowed")
    F("G3", "E2", "Bị từ chối", exit="right", enter="top", cond="rights_status = permission_denied")
    F("T7", "T8"); F("T8", "SP"); F("SP", "T9"); F("T9", "T10")
    F("BE", "T12", exit="bottom", enter="top")
    F("T12", "E3")
    F("T10", "M1", exit="bottom", enter="right")
    F("T3", "M1", exit="left", enter="top", via=[lambda D: ("x", D.lx("L_USR") + 50), lambda D: ("y", D.fy(14.1)),
                                                 lambda D: ("x", D.lx("L_USR"))])
    F("M1", "T13"); F("T13", "E4")
    d.d("T10", "DS")
    d.m("T11", "OPS", "Cảnh báo hàng chờ đầy")
    d.m("T12", "OPS", "Cảnh báo lỗi")
    return d


# ============================================================================ BP-01a Tạo một phương án
def bp01a():
    d = Diagram("BP01a", "BP-01a — Tạo một phương án (lặp tuần tự 4 lần; AS-IS, giữ nguyên ở TO-BE)")
    d.pool("P", "Pipeline AI", [("L_AI", "Sinh ảnh"), ("L_QG", "Cổng chất lượng tự động")])
    N = d.n
    N("S", "startEvent", "Bắt đầu một phương án", "P", "L_AI", 0)
    N("T1", "serviceTask", "Sinh hoa văn", "P", "L_AI", 1)
    N("BE", "boundaryEvent", "Lỗi GPU hoặc mô hình", "P", None, 1, attach="T1", attach_side="left",
      ev="error", error_name="VARIANT_FAILED", label="left")
    N("E_ERR", "endEvent", "Phương án lỗi", "P", "L_AI", 2.2, -1, ev="error", error_name="VARIANT_FAILED",
      label="below")
    N("T2", "businessRuleTask", "Cổng G2", "P", "L_QG", 2)
    N("G1", "exclusiveGateway", "Kết quả G2?", "P", "L_QG", 3, label="belowleft")
    N("T3", "serviceTask", "Đổi seed, sinh lại", "P", "L_QG", 3, 1)
    N("T4", "serviceTask", "Giữ bản ít lỗi nhất, gắn cờ không đạt", "P", "L_QG", 4, -1)
    N("M1", "exclusiveGateway", "", "P", "L_QG", 5)
    N("T5", "serviceTask", "Chọn bố cục, ghép hoa văn lên áo", "P", "L_AI", 6)
    N("T6", "serviceTask", "Hoàn thiện vùng áo", "P", "L_AI", 7)
    N("T7", "businessRuleTask", "Cổng G3", "P", "L_QG", 8)
    N("G2", "exclusiveGateway", "Kết quả G3?", "P", "L_QG", 9, label="belowleft")
    N("T8", "serviceTask", "Đổi seed, hạ độ nhiễu", "P", "L_QG", 9, 1)
    N("T9", "serviceTask", "Dùng bản ghép thô", "P", "L_QG", 10, -1)
    N("M2", "exclusiveGateway", "", "P", "L_QG", 11)
    N("E", "endEvent", "Phương án hoàn tất", "P", "L_QG", 12)
    F = d.f
    F("S", "T1"); F("T1", "T2", exit="bottom", enter="left")
    F("BE", "E_ERR", exit="left", enter="top")
    F("T2", "G1")
    F("G1", "M1", "Đạt / cảnh báo", cond="G2 ∈ {PASS, WARN}")
    F("G1", "T3", "Lỗi, dưới 3 lần", exit="right", enter="left", cond="G2 = FAIL và số lần < 3")
    F("T3", "T1", exit="top", enter="right")
    F("G1", "T4", "Lỗi, đủ 3 lần", exit="left", enter="top", cond="G2 = FAIL và số lần = 3")
    F("T4", "M1", exit="bottom", enter="left")
    F("M1", "T5", exit="bottom", enter="right")
    F("T5", "T6"); F("T6", "T7", exit="bottom", enter="left")
    F("T7", "G2")
    F("G2", "M2", "Đạt / cảnh báo", cond="G3 ∈ {PASS, WARN}")
    F("G2", "T8", "Lỗi, còn lượt", exit="right", enter="left", cond="G3 = FAIL và còn lượt thử")
    F("T8", "T6", exit="top", enter="right")
    F("G2", "T9", "Lỗi, hết lượt", exit="left", enter="top", cond="G3 = FAIL và hết lượt thử")
    F("T9", "M2", exit="bottom", enter="left")
    F("M2", "E")
    return d


# ============================================================================ BP-02 Xem, tải, chỉnh sửa thiết kế
def bp02(variant):
    tobe = variant == "TO-BE"
    d = Diagram(f"BP02_{variant.replace('-', '')}", f"BP-02 {variant} — Xem, tải và chỉnh sửa thiết kế")
    d.pool("P", PLATFORM, [("L_USR", "Nhà thiết kế"), ("L_GW", "Ứng dụng web"),
                           ("L_API", "API và kho Passport")])
    N = d.n
    N("S", "startEvent", "Mở trang Kết quả hoặc Thiết kế đã tạo", "P", "L_USR", 0)
    N("T1", "userTask", "Phóng to một thiết kế", "P", "L_USR", 1)
    N("G1", "exclusiveGateway", "Muốn làm gì?", "P", "L_USR", 2, label="belowleft")
    # tải xuống
    N("T2", "userTask", "Bấm Tải xuống", "P", "L_USR", 3, 1)
    if tobe:
        N("T3", "serviceTask", "Xuất tệp có nhãn AI và mã Passport", "P", "L_GW", 3, 0, color=NEW)
    else:
        N("T3", "scriptTask", "In nhãn AI lên ảnh, lưu tệp", "P", "L_GW", 3, 0)
    N("E_DL", "endEvent", "Đã tải ảnh có nhãn AI", "P", "L_GW", 3, 1, label="below")
    # chỉnh sửa
    N("G2", "exclusiveGateway", "Có Passport trên máy chủ?", "P", "L_GW", 4.5, 1, label="belowleft")
    N("T4", "serviceTask", "Khoá nút Tải lên chỉnh sửa, nêu lý do", "P", "L_GW", 4.5, 2)
    N("E_LOCK", "endEvent", "Không chỉnh sửa được", "P", "L_GW", 5.6, 2, label="below")
    N("T5", "manualTask", "Sửa ảnh bằng công cụ đồ họa", "P", "L_USR", 5.8)
    N("T6", "userTask", "Tải bản sửa lên, khai báo nội dung sửa", "P", "L_USR", 6.8)
    N("G3", "exclusiveGateway", "Lưu hay huỷ?", "P", "L_USR", 7.8, label="belowleft")
    N("E_CANCEL", "endEvent", "Huỷ, không lưu bản sửa", "P", "L_USR", 8.8, -1, label="below")
    N("T7", "businessRuleTask", "Kiểm tra tệp và hạn mức", "P", "L_GW", 8.8, 1)
    N("G4", "exclusiveGateway", "Hợp lệ?", "P", "L_GW", 9.8, 1, label="right")
    N("T8", "serviceTask", "Lưu phiên bản mới vào Passport", "P", "L_API", 10.8)
    N("T9", "businessRuleTask", "Chạy cổng G3 cho bản sửa, cập nhật trạng thái duyệt", "P", "L_API", 11.8)
    N("DS", "dataStoreReference", "Kho Design Passport", "P", "L_API", 11.3, 1, label="below")
    N("T10", "userTask", "Xem bản đã cập nhật", "P", "L_USR", 12.8)
    N("M_END", "exclusiveGateway", "", "P", "L_USR", 13.8)
    F = d.f
    F("S", "T1"); F("T1", "G1")
    F("G1", "T2", "Tải xuống", exit="right", enter="top", cond="người dùng bấm Tải xuống")
    F("T2", "T3", exit="right", enter="left"); F("T3", "E_DL", exit="right", enter="left")
    F("G1", "M_END", "Xong", exit="left", enter="left", via=[lambda D: ("x", D.lane_left("L_USR") + 26),
                                                             lambda D: ("y", D.fy(13.8))], cond="người dùng đóng cửa sổ")
    F("G1", "G2", "Chỉnh sửa", exit="bottom", enter="left", cond="người dùng bấm Tải lên chỉnh sửa")
    F("G2", "T4", "Không", exit="right", enter="left", cond="thiết kế thuộc bộ sinh sẵn")
    F("T4", "E_LOCK")
    F("G2", "T5", "Có", exit="bottom", enter="right", cond="có Passport trên máy chủ")
    F("T5", "T6"); F("T6", "G3")
    F("G3", "E_CANCEL", "Huỷ", exit="left", enter="top", cond="người dùng bấm Huỷ và xác nhận")
    F("G3", "T7", "Lưu", exit="bottom", enter="left", cond="người dùng xác nhận lưu")
    F("T7", "G4")
    F("G4", "T6", "Không hợp lệ", exit="left", enter="right",
      via=[lambda D: ("x", D.lane_left("L_GW") + 30), lambda D: ("y", D.fy(6.8))], cond="tệp hoặc trường sai, vượt hạn mức")
    F("G4", "T8", "Hợp lệ", exit="bottom", enter="left", cond="mọi kiểm tra đạt")
    F("T8", "T9"); F("T9", "T10", exit="bottom", enter="right"); F("T10", "M_END")
    d.d("T8", "DS", exit="right", enter="top"); d.d("T9", "DS", exit="right", enter="bottom")
    if tobe:
        N("G5", "exclusiveGateway", "Đề cử đi thẩm định?", "P", "L_USR", 14.8, label="belowleft", color=NEW)
        N("E_END", "endEvent", "Kết thúc", "P", "L_USR", 15.8, -1, label="below")
        N("T11", "userTask", "Đề cử thiết kế đi thẩm định", "P", "L_USR", 15.8, color=NEW)
        N("T12", "serviceTask", "Ghi đề cử, đưa vào hàng đợi thẩm định", "P", "L_API", 16.8, color=NEW)
        N("E_NOM", "endEvent", "Đã đề cử", "P", "L_API", 17.8, label="below")
        F("M_END", "G5")
        F("G5", "E_END", "Không", exit="left", enter="top", cond="không đề cử hoặc thiết kế sinh sẵn")
        F("G5", "T11", "Có", cond="người dùng chọn đề cử, thiết kế có Passport")
        F("T11", "T12", exit="bottom", enter="left"); F("T12", "E_NOM")
    else:
        N("E_END", "endEvent", "Kết thúc", "P", "L_USR", 14.8)
        F("M_END", "E_END")
    return d


# ============================================================================ BP-03 Kiểm soát chất lượng, thẩm định, xuất bản
def bp03_asis():
    d = Diagram("BP03_ASIS", "BP-03 AS-IS — Kiểm soát chất lượng, thẩm định và xuất bản")
    d.pool("P", PLATFORM, [("L_QC", "QC Officer"), ("L_API", "API và kho Passport")])
    d.pool("EXP", "Hội đồng chuyên gia", [("L_EXP", "Chuyên gia di sản, thiết kế")])
    N = d.n
    N("S", "startEvent", "Mở đợt thẩm định thủ công", "P", "L_QC", 0)
    N("T1", "userTask", "Lấy danh sách thiết kế", "P", "L_QC", 1)
    N("DS", "dataStoreReference", "Kho Design Passport", "P", "L_API", 1, label="below")
    N("G1", "exclusiveGateway", "Trạng thái duyệt?", "P", "L_QC", 2, label="belowleft")
    N("E1", "endEvent", "Không đưa đi thẩm định", "P", "L_QC", 3, -1, label="below")
    N("T2", "userTask", "Xem cảnh báo, ra quyết định QC", "P", "L_QC", 3, 1)
    N("G2", "exclusiveGateway", "Quyết định QC?", "P", "L_API", 4, label="belowleft")
    N("E2", "endEvent", "Trả về sửa", "P", "L_API", 5, 1, label="below")
    N("M1", "exclusiveGateway", "", "P", "L_QC", 5)
    N("T3", "userTask", "Lập gói chấm mù", "P", "L_QC", 6)
    N("T4", "sendTask", "Gửi link phiếu hoặc gói cho chuyên gia", "P", "L_QC", 7)
    N("ES", "startEvent", "Nhận gói chấm mù", "EXP", "L_EXP", 7, ev="message", label="below")
    N("ET", "userTask", "Chấm mù 5 tiêu chí, chọn quyết định", "EXP", "L_EXP", 8.3)
    N("EE", "endEvent", "Gửi phiếu", "EXP", "L_EXP", 9.6, ev="message", label="below")
    N("T5", "receiveTask", "Nhận phiếu chấm", "P", "L_QC", 9.6)
    N("T6", "userTask", "Nhập kết quả vào Passport", "P", "L_QC", 10.6)
    N("T7", "serviceTask", "Ghi phiếu, đánh dấu mâu thuẫn với quy tắc đạt", "P", "L_API", 11.6)
    N("G3", "exclusiveGateway", "Quyết định chuyên gia?", "P", "L_API", 12.6, label="belowright")
    N("E3", "endEvent", "Yêu cầu sửa, nhà thiết kế không được báo", "P", "L_API", 13.6, 1, label="below")
    N("E4", "endEvent", "Bị loại, đã ghi lý do", "P", "L_API", 13.6, 0, label="right")
    N("DS2", "dataStoreReference", "Kho Design Passport", "P", "L_API", 11.6, 1, label="below")
    N("T8", "userTask", "Yêu cầu xuất bản", "P", "L_QC", 13.6)
    N("T9", "businessRuleTask", "Kiểm tra quyền xuất bản công khai", "P", "L_API", 14.6)
    N("G4", "exclusiveGateway", "Được xuất bản?", "P", "L_API", 15.6, label="belowleft")
    N("T10", "serviceTask", "Ghi sự kiện xuất bản", "P", "L_API", 16.6)
    N("E5", "endEvent", "Đã xuất bản", "P", "L_API", 17.6)
    N("E6", "endEvent", "Không xuất bản, chỉ dùng phi thương mại", "P", "L_QC", 16.6, label="below")
    F = d.f
    F("S", "T1"); F("T1", "G1")
    F("G1", "E1", "Không đạt", exit="left", enter="top", cond="approval.status = qa_failed")
    F("G1", "T2", "Có cảnh báo", exit="right", enter="top", cond="approval.status = qa_warning")
    F("T2", "G2", exit="bottom", enter="top")
    F("G2", "E2", "Trả về sửa", exit="right", enter="top", cond="decision = return_for_repair")
    F("G2", "M1", "Chuyển chuyên gia", exit="bottom", enter="right", cond="decision = forward_to_expert")
    F("G1", "M1", "Chờ chuyên gia", cond="approval.status = pending_expert_review")
    F("M1", "T3"); F("T3", "T4")
    F("T4", "T5", exit="bottom", enter="top")
    F("ES", "ET"); F("ET", "EE")
    F("T5", "T6"); F("T6", "T7", exit="bottom", enter="left"); F("T7", "G3")
    F("G3", "E3", "Cần sửa", exit="right", enter="top", cond="decision = revise")
    F("G3", "E4", "Loại", cond="decision = reject")
    F("G3", "T8", "Đạt", exit="left", enter="top", cond="decision = approve")
    F("T8", "T9", exit="bottom", enter="left"); F("T9", "G4")
    F("G4", "T10", "Có", cond="rights_gate(publish_public).allowed")
    F("G4", "E6", "Không", exit="left", enter="top", cond="quyền chưa cho phép xuất bản")
    F("T10", "E5")
    d.d("DS", "T1"); d.d("T7", "DS2")
    d.m("T4", "ES", "Gói / link chấm mù")
    d.m("EE", "T5", "Phiếu chấm")
    return d


def bp03_tobe():
    d = Diagram("BP03_TOBE", "BP-03 TO-BE — Kiểm soát chất lượng, thẩm định và xuất bản")
    d.pool("P", PLATFORM, [("L_QC", "QC Officer"), ("L_SYS", "Hệ thống")])
    d.pool("EXP", "Hội đồng chuyên gia", [("L_EXP", "Chuyên gia di sản, thiết kế")], multi=True)
    N = d.n
    N("S", "startEvent", "Thiết kế đổi trạng thái duyệt hoặc được đề cử", "P", "L_SYS", 0, ev="conditional",
      timer="approval.status thay đổi hoặc có đề cử", color=NEW)
    N("T1", "businessRuleTask", "Định tuyến theo trạng thái duyệt", "P", "L_SYS", 1, color=NEW)
    N("DS", "dataStoreReference", "Kho Design Passport", "P", "L_SYS", 1, 1, label="below")
    N("G1", "exclusiveGateway", "Trạng thái?", "P", "L_SYS", 2, label="belowleft")
    N("E1", "endEvent", "Chờ sửa", "P", "L_SYS", 3, 1, label="below", color=NEW)
    N("T2", "userTask", "Xử lý cảnh báo trên bảng QC", "P", "L_QC", 3, color=NEW)
    N("G2", "exclusiveGateway", "Quyết định QC?", "P", "L_QC", 4, label="belowleft")
    N("E2", "endEvent", "Trả về sửa", "P", "L_QC", 5, -1, label="below")
    N("M1", "exclusiveGateway", "", "P", "L_SYS", 5)
    N("T3", "serviceTask", "Xếp hàng đợi, tạo phiếu chấm mù theo vai trò", "P", "L_SYS", 6, color=NEW)
    N("T4", "sendTask", "Gửi link phiếu cho chuyên gia", "P", "L_SYS", 7, color=NEW)
    N("M3", "exclusiveGateway", "", "P", "L_SYS", 8)
    N("EB", "eventBasedGateway", "", "P", "L_SYS", 9, color=NEW)
    N("ES", "startEvent", "Nhận link phiếu", "EXP", "L_EXP", 7, ev="message", label="below")
    N("ET", "userTask", "Chấm mù trên cổng thẩm định", "EXP", "L_EXP", 8.5, color=NEW)
    N("EE", "endEvent", "Gửi phiếu", "EXP", "L_EXP", 10, ev="message", label="below")
    N("IC1", "intermediateCatchEvent", "Nhận đủ phiếu", "P", "L_SYS", 10, ev="message", color=NEW, label="left")
    N("IC2", "intermediateCatchEvent", "Quá 7 ngày", "P", "L_SYS", 10.6, 1, ev="timer", timer="P7D", color=NEW, label="right")
    N("GR", "exclusiveGateway", "Đã nhắc 2 lần?", "P", "L_SYS", 11.6, 1, label="belowright", color=NEW)
    N("T5", "sendTask", "Nhắc chuyên gia", "P", "L_SYS", 11.6, 2, color=NEW)
    N("T5b", "userTask", "Mời chuyên gia khác", "P", "L_QC", 11.6, color=NEW)
    N("T6", "businessRuleTask", "Tổng hợp phiếu, đánh dấu mâu thuẫn", "P", "L_SYS", 12.6)
    N("DS2", "dataStoreReference", "Kho Design Passport", "P", "L_SYS", 12.6, 1, label="below")
    N("G3", "exclusiveGateway", "Có mâu thuẫn quy tắc?", "P", "L_SYS", 13.2, label="belowleft")
    N("T7", "userTask", "Xem lại phiếu mâu thuẫn, chốt kết luận", "P", "L_QC", 14.2, color=NEW)
    N("M2", "exclusiveGateway", "", "P", "L_SYS", 15.2)
    N("G4", "exclusiveGateway", "Kết luận?", "P", "L_SYS", 16.2, label="belowleft")
    N("T8", "serviceTask", "Ghi lý do, mở lại để sửa", "P", "L_SYS", 17.2, 1)
    N("E3", "endEvent", "Chờ chỉnh sửa", "P", "L_SYS", 18.2, 1, label="below")
    N("E4", "endEvent", "Bị loại, đã ghi lý do", "P", "L_QC", 17.2, label="below")
    N("T9", "businessRuleTask", "Kiểm tra quyền xuất bản công khai", "P", "L_SYS", 17.2)
    N("G5", "exclusiveGateway", "Được xuất bản?", "P", "L_SYS", 18.2, label="belowleft")
    N("T10", "serviceTask", "Xuất bản kèm nhãn AI, ghi công", "P", "L_SYS", 19.2, color=NEW)
    N("E5", "endEvent", "Đã xuất bản", "P", "L_SYS", 20.2)
    N("E6", "endEvent", "Đã phê duyệt, chờ giấy phép", "P", "L_QC", 19.2, label="below")
    F = d.f
    F("S", "T1"); F("T1", "G1")
    F("G1", "E1", "Không đạt", exit="right", enter="top", cond="approval.status = qa_failed")
    F("G1", "T2", "Có cảnh báo", exit="left", enter="top", cond="approval.status = qa_warning")
    F("T2", "G2")
    F("G2", "E2", "Trả về sửa", exit="left", enter="top", cond="decision = return_for_repair")
    F("G2", "M1", "Chuyển chuyên gia", exit="bottom", enter="left", cond="decision = forward_to_expert")
    F("G1", "M1", "Chờ chuyên gia hoặc được đề cử", cond="approval.status = pending_expert_review")
    F("M1", "T3"); F("T3", "T4"); F("T4", "M3"); F("M3", "EB")
    F("EB", "IC1"); F("EB", "IC2", exit="right", enter="top")
    F("IC2", "GR")
    F("GR", "T5", "Chưa", exit="right", enter="left", cond="số lần nhắc < 2")
    F("T5", "M3", exit="top", enter="right")
    F("GR", "T5b", "Rồi", exit="left", enter="right", cond="số lần nhắc = 2")
    F("T5b", "T4", exit="top", enter="left")
    F("IC1", "T6")
    F("ES", "ET"); F("ET", "EE")
    F("T6", "G3")
    F("G3", "T7", "Có", exit="left", enter="top", cond="rule_conflict = true")
    F("G3", "M2", "Không", cond="rule_conflict = false")
    F("T7", "M2", exit="bottom", enter="left")
    F("M2", "G4")
    F("G4", "T8", "Cần sửa", exit="right", enter="top", cond="kết luận = revise")
    F("G4", "E4", "Loại", exit="left", enter="top", cond="kết luận = reject")
    F("G4", "T9", "Đạt", cond="kết luận = approve")
    F("T8", "E3")
    F("T9", "G5")
    F("G5", "T10", "Có", cond="rights_gate(publish_public).allowed")
    F("G5", "E6", "Không", exit="left", enter="top", cond="quyền chưa cho phép xuất bản")
    F("T10", "E5")
    d.d("DS", "T1"); d.d("T6", "DS2")
    d.m("T4", "ES", "Link phiếu chấm mù")
    d.m("EE", "IC1", "Phiếu chấm")
    d.m("T5", "EXP", "Lời nhắc")
    return d


# ============================================================================ BP-04 Tiếp nhận hiện vật, quản lý quyền
def bp04(variant):
    tobe = variant == "TO-BE"
    d = Diagram(f"BP04_{variant.replace('-', '')}", f"BP-04 {variant} — Tiếp nhận hiện vật và quản lý quyền sử dụng")
    d.pool("P", PLATFORM, [("L_DATA", "Người quản lý dữ liệu"), ("L_SYS", "Hệ thống tiếp nhận")])
    d.pool("OWN", "Chủ sở hữu ảnh", black_box=True, side="left")
    N = d.n
    N("S", "startEvent", "Có ảnh hoặc mô hình hiện vật mới", "P", "L_DATA", 0)
    N("T1", "userTask", "Chuẩn bị ảnh, khai báo nguồn, đơn vị lưu giữ", "P", "L_DATA", 1)
    N("T2", "serviceTask", "Tiếp nhận: tách nền, kiểm tiêu chí C1–C4", "P", "L_SYS", 2)
    N("G1", "exclusiveGateway", "Đạt C1 và C2?", "P", "L_SYS", 3, label="belowleft")
    N("T3", "serviceTask", "Đánh dấu loại, ghi lý do", "P", "L_SYS", 4, 1)
    N("E1", "endEvent", "Không đưa vào thư viện", "P", "L_SYS", 4, 2, label="below")
    N("T4", "businessRuleTask", "Xác định tình trạng quyền", "P", "L_SYS", 4)
    N("G2", "exclusiveGateway", "Tình trạng quyền?", "P", "L_SYS", 5, label="belowleft")
    N("E2", "endEvent", "Không được dùng", "P", "L_SYS", 6, 1, label="below")
    N("T5", "manualTask", "Gửi đề nghị cấp phép", "P", "L_DATA", 6)
    if tobe:
        N("T5b", "serviceTask", "Ghi trạng thái chờ cấp phép", "P", "L_SYS", 6, -1, color=NEW)
        N("EB", "eventBasedGateway", "", "P", "L_SYS", 7, -1, color=NEW)
        N("IC1", "intermediateCatchEvent", "Nhận phản hồi", "P", "L_SYS", 8, -1, ev="message", color=NEW, label="left")
        N("IC2", "intermediateCatchEvent", "Quá 14 ngày", "P", "L_SYS", 8, 1, ev="timer", timer="P14D", color=NEW,
          label="below")
        N("G3", "exclusiveGateway", "Đã nhắc 2 lần?", "P", "L_SYS", 9, 1, label="belowright", color=NEW)
        N("T5c", "sendTask", "Gửi lời nhắc", "P", "L_DATA", 9, color=NEW)
        N("T6", "userTask", "Ghi phản hồi vào biểu mẫu quyền", "P", "L_DATA", 10.4, -1,
          color=NEW)
        N("E3", "endEvent", "Đóng đề nghị, giữ \"chưa xác minh\"", "P", "L_SYS", 10, 2, label="below", color=NEW)
    else:
        N("T6", "userTask", "Sửa trạng thái quyền thủ công", "P", "L_DATA", 7)
    M_STEP = 10.4 if tobe else 8
    N("M1", "exclusiveGateway", "", "P", "L_SYS", M_STEP)
    N("T7", "serviceTask", "Ghi vào danh mục hiện vật", "P", "L_SYS", M_STEP + 1)
    N("DS", "dataStoreReference", "Danh mục hiện vật", "P", "L_SYS", M_STEP + 1, 1, label="below")
    N("T8", "userTask", "Viết mô tả, ý nghĩa hoa văn", "P", "L_DATA", M_STEP + 2)
    if tobe:
        N("T9", "serviceTask", "Tự xuất dữ liệu web và mô hình 3D", "P", "L_SYS", M_STEP + 3, color=NEW)
    else:
        N("T9", "userTask", "Xuất dữ liệu web và mô hình 3D", "P", "L_DATA", M_STEP + 3)
    N("E4", "endEvent", "Hiện vật có trên Studio", "P", "L_DATA" if not tobe else "L_SYS", M_STEP + 4)
    F = d.f
    F("S", "T1"); F("T1", "T2", exit="bottom", enter="left"); F("T2", "G1")
    F("G1", "T3", "Không", exit="right", enter="top", cond="C1 hoặc C2 = FAIL")
    F("T3", "E1", exit="right", enter="left")
    F("G1", "T4", "Có", cond="C1, C2 không FAIL")
    F("T4", "G2")
    F("G2", "E2", "Bị từ chối", exit="right", enter="top", cond="rights_status = permission_denied")
    F("G2", "T5", "Chưa xác minh", exit="left", enter="top", cond="rights_status = unverified")
    F("G2", "M1", "Đã có quyền", cond="rights_status ∈ publishable_statuses")
    if tobe:
        F("T5", "T5b", exit="right", enter="left"); F("T5b", "EB")
        F("EB", "IC1"); F("EB", "IC2", exit="right", enter="top")
        F("IC2", "G3")
        F("G3", "T5c", "Chưa", exit="left", enter="right", cond="số lần nhắc < 2")
        F("T5c", "EB", exit="top", enter="left")
        F("G3", "E3", "Rồi", exit="right", enter="top", cond="số lần nhắc = 2")
        F("IC1", "T6", exit="bottom", enter="top", via=[lambda D: ("y", D.fy(9.6))])
        F("T6", "M1", exit="right", enter="left")
        d.m("T5c", "OWN", "Lời nhắc", offset=0)
    else:
        F("T5", "T6"); F("T6", "M1", exit="bottom", enter="left")
    F("M1", "T7"); F("T7", "T8", exit="bottom", enter="right" if not tobe else "right")
    if tobe:
        F("T8", "T9", exit="bottom", enter="left"); F("T9", "E4")
    else:
        F("T8", "T9"); F("T9", "E4")
    d.d("T7", "DS")
    d.m("T5", "OWN", "Đề nghị cấp phép")
    if tobe:
        d.m("OWN", "IC1", "Phản hồi")
    return d


MODELS = {
    "BP-00_ban-do-quy-trinh_AS-IS": lambda: bp00("AS-IS"),
    "BP-00_ban-do-quy-trinh_TO-BE": lambda: bp00("TO-BE"),
    "BP-01_tao-thiet-ke": bp01,
    "BP-01a_tao-mot-phuong-an": bp01a,
    "BP-02_xem-tai-chinh-sua_AS-IS": lambda: bp02("AS-IS"),
    "BP-02_xem-tai-chinh-sua_TO-BE": lambda: bp02("TO-BE"),
    "BP-03_kiem-soat-tham-dinh-xuat-ban_AS-IS": bp03_asis,
    "BP-03_kiem-soat-tham-dinh-xuat-ban_TO-BE": bp03_tobe,
    "BP-04_tiep-nhan-hien-vat_AS-IS": lambda: bp04("AS-IS"),
    "BP-04_tiep-nhan-hien-vat_TO-BE": lambda: bp04("TO-BE"),
}
