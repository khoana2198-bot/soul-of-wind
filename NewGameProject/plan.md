# Game Design Document (GDD)

## 1. Game Overview
**Game Title:** Soul of Wind (Tên tạm thời)
**Genre:** Open-world Adventure RPG (Phiêu lưu thế giới mở, Nhập vai)
**Target Audience:** Casual players, fans of exploration and collection.
**Platform:** PC (Windows)

## 2. Gameplay Mechanics (Cơ chế Game)
- **Core Loop:**
  - **Exploration:** Khám phá thế giới rộng lớn, thư giãn.
  - **Progression:** Nâng cấp chỉ số, thu thập thú cưng (Pets).
  - **Dynamic Skill System (AI):** Hệ thống kỹ năng "thông minh".
    - *Logic:* Theo dõi hành vi người chơi để mở khóa kỹ năng tương ứng.
    - *Example:* Bị rượt đuổi nhiều -> Kỹ năng "Dash/Chạy nhanh". Trộm đồ thành công -> Kỹ năng "Stealth/Tàng hình".
- **Controls:**
  - **WASD:** Di chuyển.
  - **Space:** Nhảy / Tương tác.
  - **Auto-Sprint:** Tự động chạy nhanh khi out-combat (không tốn thể lực).
  - **Mouse Left:** Đánh thường.
- **Objectives:** Đánh bại Boss khu vực, tham gia sự kiện thế giới (World Events).
- **Multiplayer:** Hỗ trợ nhiều người chơi online (Client-Server architecture).

## 3. Story & Characters (Cốt truyện & Nhân vật)
- **Setting:** Fantasy World (Thế giới giả tưởng) - Peaceful & Relaxing.
- **Main Character:** Custom Character (Tùy chỉnh nhân vật).
- **Plot:** Non-linear. Cốt truyện ẩn trong NPC và sự kiện.

## 4. Visual & Audio (Hình ảnh & Âm thanh)
- **Art Style:** Pixel Art (Top-down 2.5D). Ưu tiên màu sắc tươi sáng, nhẹ nhàng.
- **Audio:** Nhạc nền Piano/Orchestra thư giãn, âm thanh tự nhiên (gió, nước chảy).

## 5. Technical Requirements (Yêu cầu Kỹ thuật)
- **Engine/Language:** Python (Library: `pygame` cho Client, `socket` cho Server).
  - *Reason:* Python mạnh mẽ, dễ chỉnh sửa logic "AI", hỗ trợ tốt networking cơ bản.
- **Key Features:**
  - **Networking:** Multi-client handling.
  - **Procedural Generation:** Tạo sự kiện/quái ngẫu nhiên.
  - **Data Persistence:** Lưu trữ nhân vật (Database/Json).
