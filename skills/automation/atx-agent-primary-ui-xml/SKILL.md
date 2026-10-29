---

name: atx-agent-primary-ui-xml

description: Đưa atx-agent (port 7912) lên làm cơ chế PRIMARY đọc UI XML trên farm Android yếu (S7/Android 7) — khi shell uiautomator dump bị Killed (EXIT=137) và file fallback trả XML stale. Dùng khi flow reg/UI automation fail vì đọc nhầm màn cũ, type nhầm field, hoặc khi cần patch get_ui_xml/ui_xml ở bất kỳ repo automation nào.

---


## References
- Chi tiết toàn bộ quy trình, case study và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
