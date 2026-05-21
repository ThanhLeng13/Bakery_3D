# Requirements Document

## Introduction

Ứng dụng Web Bán Bánh Kem Tích Hợp AI là một hệ thống thương mại điện tử chuyên biệt cho tiệm bánh kem tùy chỉnh tại TP.HCM. Hệ thống cho phép khách hàng xem menu, thiết kế bánh kem theo ý muốn thông qua công cụ Click-to-Customize trực quan, tư vấn với AI chatbot, và đặt hàng trực tuyến. Quản trị viên có thể quản lý sản phẩm, đơn hàng và theo dõi hoạt động kinh doanh.

Phạm vi Phase 1 (1.5 tháng): Catalog sản phẩm, Cake Builder, AI Chatbot, Đặt hàng cơ bản, Admin Dashboard cơ bản, Xác thực người dùng.

Phạm vi mở rộng (Đồ án tốt nghiệp): Tích hợp VNPay, Zalo OA, AI gợi ý sản phẩm, Quản lý lịch sản xuất, Thống kê nâng cao.

## Glossary

- **System**: Toàn bộ ứng dụng Web Bán Bánh Kem Tích Hợp AI
- **Catalog_Service**: Module quản lý và hiển thị danh mục sản phẩm bánh kem
- **Cake_Builder**: Công cụ Click-to-Customize cho phép khách hàng thiết kế bánh kem trực quan bằng SVG
- **AI_Chatbot**: Module tư vấn tích hợp Claude API sử dụng kiến trúc RAG
- **Order_Service**: Module xử lý đặt hàng, quản lý trạng thái đơn hàng
- **Auth_Service**: Module xác thực và phân quyền người dùng (Supabase Auth)
- **Admin_Dashboard**: Giao diện quản trị cho chủ tiệm bánh
- **Customer**: Người dùng cuối truy cập hệ thống để xem, thiết kế và đặt bánh kem
- **Admin**: Chủ tiệm bánh quản lý toàn bộ hệ thống
- **Baker**: Thợ làm bánh xem và cập nhật trạng thái đơn hàng
- **Customization_Zone**: Vùng tương tác trên mô hình SVG bánh kem (top, body, border)
- **Pickup_Schedule**: Lịch hẹn nhận bánh tại cửa hàng
- **AI_Summary**: Bản tóm tắt đơn hàng được AI tạo tự động từ thông tin tùy chỉnh

## Requirements

### Requirement 1: Hiển thị danh mục sản phẩm

**User Story:** Là một Customer, tôi muốn xem danh mục bánh kem với hình ảnh và thông tin chi tiết, để tôi có thể lựa chọn sản phẩm phù hợp.

#### Acceptance Criteria

1. WHEN a Customer navigates to the product catalog page, THE Catalog_Service SHALL display all available products grouped by category (bánh âu, bánh ngọt) with product image, name, base price, and short description (maximum 100 characters), sorted by newest first within each category, paginated at 20 products per page
2. WHEN a Customer selects a product category filter, THE Catalog_Service SHALL display only products belonging to the selected category within 500ms
3. WHEN a Customer selects a specific product, THE Catalog_Service SHALL display the product detail page including full description (maximum 500 characters), available sizes (16cm, 20cm, 24cm, 2-tier), flavor options, and price breakdown showing base price per size and additional cost per flavor option
4. WHILE the catalog page is loading, THE Catalog_Service SHALL display skeleton loading placeholders matching the final layout dimensions and positions
5. IF a product has no available stock or is marked inactive, THEN THE Catalog_Service SHALL hide that product from the Customer-facing catalog
6. THE Catalog_Service SHALL render the product catalog page within 2 seconds on a simulated 3G mobile connection (750kbps throughput, 200ms RTT)
7. IF no products are available in the catalog or selected category, THEN THE Catalog_Service SHALL display an empty state message indicating no products are currently available
8. IF a product image fails to load, THEN THE Catalog_Service SHALL display a default placeholder image in place of the failed product image

### Requirement 2: Thiết kế bánh kem tùy chỉnh (Cake Builder)

**User Story:** Là một Customer, tôi muốn thiết kế bánh kem theo ý muốn bằng công cụ trực quan, để tôi có thể tạo ra chiếc bánh độc đáo cho dịp đặc biệt.

#### Acceptance Criteria

1. WHEN a Customer opens the Cake Builder, THE Cake_Builder SHALL render an interactive SVG cake model within 2 seconds, displaying visually distinct Customization_Zones (top, body, border) that highlight when hovered or tapped
2. WHEN a Customer clicks on a Customization_Zone, THE Cake_Builder SHALL display the available customization options for that zone (color, decoration, topping) within 100ms
3. WHEN a Customer selects a customization option, THE Cake_Builder SHALL update the SVG model to reflect the selected change within 100ms
4. WHEN a Customer selects a cake size, THE Cake_Builder SHALL update the displayed price based on the selected size (16cm, 20cm, 24cm, 2-tier) and current customizations within 200ms
5. THE Cake_Builder SHALL calculate and display the total price within 200ms of any customization change made by the Customer
6. WHEN a Customer confirms the cake design by clicking the completion action, THE Cake_Builder SHALL validate that all mandatory fields (size, flavor, cream_type, cream_color) are selected, and store the customization data as a JSON object containing size, flavor, cream_type, cream_color, topping_type, and special_notes (maximum 200 characters)
7. IF a Customer attempts to confirm the cake design with any mandatory field (size, flavor, cream_type, cream_color) not selected, THEN THE Cake_Builder SHALL display an error message indicating which fields are missing and SHALL NOT proceed to completion
8. WHEN a Customer completes the cake design, THE Cake_Builder SHALL generate a visual preview image of the final customized cake
9. IF a Customer leaves the Cake Builder page without completing the design, THEN THE Cake_Builder SHALL save the current design state to local storage for recovery on next visit
10. IF local storage is unavailable or full when attempting to save design state, THEN THE Cake_Builder SHALL display a warning message indicating that the design cannot be saved for later recovery
11. THE Cake_Builder SHALL support touch interactions on mobile devices (minimum viewport width 320px) with the same 100ms response threshold as desktop click interactions

### Requirement 3: AI Chatbot tư vấn

**User Story:** Là một Customer, tôi muốn được AI tư vấn chọn bánh phù hợp theo dịp và sở thích, để tôi có thể đưa ra quyết định mua hàng tốt hơn.

#### Acceptance Criteria

1. WHEN a Customer opens the AI chatbot, THE AI_Chatbot SHALL display a greeting message and prompt the Customer to describe their needs (dịp, số người, ngân sách)
2. WHEN a Customer sends a message, THE AI_Chatbot SHALL respond with a consultation message that addresses the Customer's stated criteria (occasion, quantity, budget, flavor preference) within 5 seconds
3. THE AI_Chatbot SHALL use the product catalog as context (RAG) to provide recommendations that reference actual available products with pricing matching the current catalog values
4. WHEN a Customer describes an occasion (sinh nhật, đám cưới, kỷ niệm), THE AI_Chatbot SHALL suggest between 2 and 5 cake options from the catalog, each including the product name, price, and a one-sentence reasoning explaining why it fits the occasion
5. WHEN a Customer confirms a cake selection through the chatbot, THE AI_Chatbot SHALL generate an AI_Summary containing all order details in structured format including: size, flavor, decorations, pickup date, and total price, where all fields must be present before the summary is generated
6. THE AI_Chatbot SHALL maintain conversation context for up to 20 messages within a single chat session to provide coherent multi-turn dialogue
7. IF the Claude API is unavailable or returns an error, THEN THE AI_Chatbot SHALL display an error message indicating the service is temporarily unavailable and suggest the Customer try again or contact the shop directly via phone number
8. THE AI_Chatbot SHALL respond in Vietnamese language matching the Customer input language
9. IF no products in the catalog match the Customer's stated criteria, THEN THE AI_Chatbot SHALL inform the Customer that no exact matches were found and suggest the closest available alternatives or prompt the Customer to adjust their criteria
10. IF the Customer's message is ambiguous or missing required information (occasion, size, or budget), THEN THE AI_Chatbot SHALL ask a follow-up question to clarify the missing details before providing recommendations

### Requirement 4: Đặt hàng và chọn lịch nhận bánh

**User Story:** Là một Customer, tôi muốn đặt hàng bánh kem và chọn thời gian nhận bánh, để tôi có thể nhận bánh đúng dịp cần thiết.

#### Acceptance Criteria

1. WHEN a Customer submits an order, THE Order_Service SHALL create an order record with status "pending" containing product name, size, flavor, customization data, pickup date, Customer full name, phone number, and email
2. WHEN a Customer selects a Pickup_Schedule, THE Order_Service SHALL validate that the selected date is at least 24 hours from the current time for standard cakes and at least 48 hours for 2-tier cakes, and no more than 30 days in advance
3. IF a Customer selects a Pickup_Schedule that violates the minimum lead time or maximum advance booking limit, THEN THE Order_Service SHALL reject the selection, display a validation message indicating the allowed date range, and prevent order submission
4. WHEN an order is successfully created, THE Order_Service SHALL display an order confirmation with order ID, total price, pickup date, and a summary of ordered items to the Customer
5. IF an unauthenticated user attempts to submit an order, THEN THE Order_Service SHALL redirect the user to the login page and preserve the cart contents for order submission after authentication
6. WHEN a Customer views their order history, THE Order_Service SHALL display orders paginated at 10 orders per page, sorted by creation date descending, with status (pending, confirmed, in_production, ready, delivered), pickup date, and total price
7. IF a Customer submits an order with incomplete required fields (full name, phone number, pickup date, or at least one product), THEN THE Order_Service SHALL highlight the missing fields and display a validation message indicating which fields are required
8. WHEN a Customer adds a cake from the Cake Builder to the order, THE Order_Service SHALL include the complete customization_json and AI_Summary in the order record

### Requirement 5: Xác thực và phân quyền người dùng

**User Story:** Là một Customer, tôi muốn đăng ký và đăng nhập tài khoản một cách an toàn, để tôi có thể quản lý đơn hàng và thông tin cá nhân.

#### Acceptance Criteria

1. WHEN a Customer registers, THE Auth_Service SHALL create a new account with email (maximum 254 characters), password (hashed, minimum 8 characters and maximum 128 characters containing at least one uppercase letter, one lowercase letter, and one digit), full name (maximum 100 characters), and phone number (10-digit Vietnamese format)
2. WHEN a Customer logs in with valid credentials, THE Auth_Service SHALL issue a JWT token with a 1-hour expiration and redirect to the previous page within 2 seconds
3. WHEN a Customer logs in via Google OAuth2, THE Auth_Service SHALL authenticate through Supabase Auth and link to an existing account if the email matches, or create a new account otherwise
4. IF a Customer provides invalid login credentials, THEN THE Auth_Service SHALL display a generic error message without revealing whether the email or password is incorrect and limit login attempts to a maximum of 5 failed attempts per 15-minute window per email address
5. THE Auth_Service SHALL enforce role-based access control with three roles (Customer, Admin, and Baker) by denying access and displaying an unauthorized indication when a user attempts to access a resource outside their assigned role
6. WHILE a Customer session is active, THE Auth_Service SHALL refresh the JWT token automatically when less than 5 minutes remain before expiration, without requiring re-authentication or page reload
7. IF a JWT token is expired or invalid, THEN THE Auth_Service SHALL redirect the user to the login page and clear local session data
8. IF a Customer submits a registration form with a duplicate email, invalid phone format, or password that does not meet the minimum requirements, THEN THE Auth_Service SHALL reject the registration and display an error message indicating which field failed validation
9. IF a Customer exceeds 5 failed login attempts within 15 minutes, THEN THE Auth_Service SHALL lock the account for that email for 15 minutes and display a message indicating the account is temporarily locked
10. WHEN a Customer registers successfully, THE Auth_Service SHALL assign the Customer role by default

### Requirement 6: Quản lý sản phẩm (Admin)

**User Story:** Là một Admin, tôi muốn quản lý danh mục sản phẩm bánh kem, để tôi có thể cập nhật menu và giá cả kịp thời.

#### Acceptance Criteria

1. WHEN an Admin creates a new product, THE Admin_Dashboard SHALL save the product with name (1-200 characters), description (1-2000 characters), category, base price (1,000 to 999,999,999 VND), available sizes (1 to 10 options), images (1 to 10 files), and active status, where name, category, and base price are required fields
2. IF an Admin submits a new product form with any required field missing or any field value outside its valid range, THEN THE Admin_Dashboard SHALL reject the submission and display an error message indicating which fields are invalid
3. WHEN an Admin updates a product, THE Admin_Dashboard SHALL reflect the changes on the Customer-facing catalog within 5 seconds after successful save
4. WHEN an Admin uploads a product image, THE Admin_Dashboard SHALL validate that the image is in JPEG, PNG, or WebP format, does not exceed 5 MB in file size, and resize to a maximum of 1200x1200 pixels while preserving aspect ratio
5. IF an Admin uploads a product image that exceeds 5 MB or is not in JPEG, PNG, or WebP format, THEN THE Admin_Dashboard SHALL reject the upload and display an error message indicating the validation failure reason
6. WHEN an Admin deactivates a product, THE Admin_Dashboard SHALL remove the product from the Customer-facing catalog without deleting the database record
7. THE Admin_Dashboard SHALL display a paginated product list with 20 items per page, with search by product name (minimum 1 character) and filter capabilities by category and status

### Requirement 7: Quản lý đơn hàng (Admin)

**User Story:** Là một Admin, tôi muốn xem và quản lý tất cả đơn hàng, để tôi có thể điều phối sản xuất và giao hàng hiệu quả.

#### Acceptance Criteria

1. WHEN an Admin views the order management page, THE Admin_Dashboard SHALL display orders in a paginated list (maximum 20 orders per page) sorted by creation date descending (newest first) with status, Customer name, pickup date, and total price
2. WHEN an Admin updates an order status, THE Order_Service SHALL transition the order to the new status following the sequence (pending → confirmed → in_production → ready → delivered), record the timestamp, and display a confirmation indicating the new status
3. WHEN an Admin views an order detail, THE Admin_Dashboard SHALL display the complete order information including customization details, AI_Summary, Customer contact information (name, phone, email), and the status change history with timestamps
4. THE Admin_Dashboard SHALL allow filtering orders by status, date range, and Customer name (partial match, minimum 2 characters) and display an empty state message when no orders match the filter criteria
5. IF an Admin attempts to transition an order to an invalid status, THEN THE Order_Service SHALL reject the transition and display the valid next statuses for the current order state

### Requirement 8: Cập nhật trạng thái đơn hàng (Baker)

**User Story:** Là một Baker, tôi muốn xem đơn hàng được giao và cập nhật tiến độ, để Admin và Customer biết được tình trạng đơn hàng.

#### Acceptance Criteria

1. WHEN a Baker logs in, THE Admin_Dashboard SHALL display all orders with status "confirmed" or "in_production" sorted by pickup date ascending, showing order ID, Customer name, pickup date, and current status
2. WHEN a Baker updates an order status to "in_production" or "ready", THE Order_Service SHALL record the status change with timestamp and Baker identifier, following the valid transitions: "confirmed" → "in_production" → "ready"
3. IF a Baker attempts to transition an order to a status that does not follow the valid sequence (confirmed → in_production → ready), THEN THE Order_Service SHALL reject the update and display the valid next status for the current order state
4. WHEN a Baker views an order, THE Admin_Dashboard SHALL display the customization details, AI_Summary, baker_notes, and pickup date in a dedicated order detail section above any secondary information
5. THE Admin_Dashboard SHALL allow a Baker to add or edit production notes (baker_notes) of up to 500 characters to an order for internal communication

### Requirement 9: Responsive Design và Performance

**User Story:** Là một Customer, tôi muốn truy cập website mượt mà trên mọi thiết bị, để tôi có thể xem và đặt bánh bất cứ lúc nào.

#### Acceptance Criteria

1. THE System SHALL render all pages on viewport widths from 320px (mobile) to 1920px (desktop) following mobile-first design approach, without horizontal scrolling, with all interactive elements reachable and text readable at the device's default zoom level
2. THE System SHALL achieve a Lighthouse Performance score of at least 80 on mobile devices
3. THE System SHALL use the design system colors: pink pastel (#E8837A), cream (#FDF6EE), mocha (#5C3D2E) consistently across all pages
4. THE System SHALL use Playfair Display font for headings and DM Sans font for body text across all pages
5. THE System SHALL render all pages without layout breakage and with all interactive features functional on the latest two versions of Chrome, Safari, Firefox, and Edge browsers
6. WHILE images are loading, THE System SHALL display placeholder elements matching the final rendered dimensions of the image to prevent layout shift (CLS < 0.1)
7. THE System SHALL ensure all interactive elements (buttons, links, form inputs) have a minimum touch target size of 44×44 CSS pixels on viewports below 768px

### Requirement 10: Đánh giá sản phẩm

**User Story:** Là một Customer, tôi muốn đánh giá sản phẩm sau khi nhận bánh, để tôi có thể chia sẻ trải nghiệm và giúp khách hàng khác tham khảo.

#### Acceptance Criteria

1. WHEN a Customer has a delivered order within the last 30 days, THE System SHALL allow the Customer to submit a review with rating (1-5 stars) and an optional text comment of up to 1000 characters for each product in the order
2. WHEN a Customer submits a review, THE System SHALL associate the review with the specific product and order, and display it on the product detail page
3. THE Catalog_Service SHALL display the average rating rounded to 1 decimal place and total review count on each product card in the catalog
4. IF a Customer attempts to review a product from an order that is not in "delivered" status, THEN THE System SHALL prevent the review submission and display an error message indicating that only products from delivered orders can be reviewed
5. THE System SHALL display reviews on the product detail page sorted by most recent first with Customer name and rating visible, showing 10 reviews per page with pagination controls
6. IF a Customer attempts to submit a review for a product they have already reviewed in the same order, THEN THE System SHALL prevent the duplicate submission and display an error message indicating that the product has already been reviewed for that order
