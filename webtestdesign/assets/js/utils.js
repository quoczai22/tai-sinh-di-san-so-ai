/**
 * UTILS.JS - Các hàm tiện ích dùng lại (format date, validate, DOM helpers...)
 */

/**
 * Format ngày tháng định dạng DD/MM/YYYY
 * @param {Date|string} date 
 * @returns {string}
 */
function formatDate(date) {
    const d = new Date(date);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
}

/**
 * Rút gọn cú pháp querySelector
 * @param {string} selector 
 * @returns {Element|null}
 */
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);
