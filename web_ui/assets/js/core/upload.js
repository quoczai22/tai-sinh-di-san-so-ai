// core/upload.js — ĐỌC TỆP ẢNH thành chuỗi base64 để gửi lên API chỉnh sửa (trang #/edit).
// Ra: fileToBase64(file) → chuỗi base64 thuần (không có tiền tố "data:"). Chỉ chạy trong trình duyệt (dùng FileReader).

export function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Không đọc được tệp ảnh.'));
        reader.onload = () => resolve(String(reader.result).split(',').pop());
        reader.readAsDataURL(file);
    });
}
