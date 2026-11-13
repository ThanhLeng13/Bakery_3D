/**
 * Chuẩn hoá lỗi API thành thông báo hiển thị được.
 *
 * VÌ SAO CẦN FILE NÀY
 * -------------------
 * `detail` từ backend có BA dạng khác nhau, và trang đăng ký chỉ xử lý được
 * một dạng:
 *
 *   1. Chuỗi               — `{"detail": "Registration failed"}`
 *      do `_handle_auth_error` trong `backend/app/api/v1/endpoints/auth.py` trả.
 *
 *   2. Mảng {field,message} — `{"detail": [{"field": "email", "message": "..."}]}`
 *      do `ValidationError` ở tầng dịch vụ trả.
 *
 *   3. Mảng {loc,msg,type}  — `{"detail": [{"type": "...", "loc": ["body","password"],
 *      "msg": "String should have at least 8 characters"}]}`
 *      do CHÍNH FastAPI trả khi `RegisterRequest` không hợp lệ.
 *
 * Dạng 3 là dạng hay gặp nhất khi người dùng nhập sai, nhưng trang đăng ký đọc
 * `e.field` và `e.message` — hai khoá KHÔNG tồn tại trong dạng này. Kết quả đo
 * được: bấm Đăng ký mà **không có thông báo nào hiện ra**, form đứng im như
 * chưa bấm. Đây là lỗi im lặng, khó lần ra hơn cả một thông báo sai.
 *
 * Ngoài ra còn một trường hợp không phải lỗi HTTP: `fetch` thất bại vì không
 * gọi được máy chủ. Khi đó không có `status`, và thông báo chung chung "Đã xảy
 * ra lỗi, vui lòng thử lại sau" không nói cho người dùng biết điều quan trọng
 * nhất — rằng máy chủ đang không chạy.
 */

export interface NormalizedApiError {
  /** Lỗi gắn với từng trường, khoá là tên trường trên form. */
  fieldErrors: Record<string, string>;
  /** Lỗi chung; rỗng khi mọi lỗi đã gắn được vào trường cụ thể. */
  generalError: string;
}

/** Nhãn tiếng Việt của các trường, dùng khi FastAPI chỉ nói "Field required". */
const FIELD_LABELS: Record<string, string> = {
  email: "email",
  password: "mật khẩu",
  new_password: "mật khẩu mới",
  full_name: "họ tên",
  phone: "số điện thoại",
};

/**
 * Dịch các thông báo kiểm tra dữ liệu hay gặp của FastAPI/Pydantic.
 *
 * Chỉ dịch những mẫu thực sự gặp ở các form hiện có. Mẫu lạ thì giữ nguyên văn
 * tiếng Anh — hiển thị đúng nguyên văn vẫn hơn là bịa một câu tiếng Việt sai ý.
 */
function dichThongBao(type: string, msg: string, field: string): string {
  const nhan = FIELD_LABELS[field] ?? field;

  if (type === "missing") return `Vui lòng nhập ${nhan}`;

  const ngan = msg.match(/at least (\d+) characters?/i);
  if (ngan) return `${hoaDauDong(nhan)} phải có ít nhất ${ngan[1]} ký tự`;

  const dai = msg.match(/at most (\d+) characters?/i);
  if (dai) return `${hoaDauDong(nhan)} không được quá ${dai[1]} ký tự`;

  if (/valid email address/i.test(msg)) return "Email không hợp lệ";

  return msg;
}

function hoaDauDong(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Lấy tên trường từ `loc` của FastAPI, ví dụ ["body","password"] -> "password". */
function truongTuLoc(loc: unknown): string | null {
  if (!Array.isArray(loc)) return null;
  const parts = loc.filter(
    (p): p is string => typeof p === "string" && p !== "body" && p !== "query",
  );
  return parts.length ? parts[parts.length - 1] : null;
}

export function normalizeApiError(err: unknown): NormalizedApiError {
  const fieldErrors: Record<string, string> = {};
  const chung: string[] = [];

  if (typeof err !== "object" || err === null) {
    return {
      fieldErrors,
      generalError: "Đã xảy ra lỗi, vui lòng thử lại sau",
    };
  }

  const e = err as {
    detail?: unknown;
    status?: unknown;
    retry_after?: unknown;
  };

  // `status` chỉ được gán trong `handleResponse`. Không có nghĩa là `fetch` đã
  // thất bại trước khi tới được máy chủ.
  if (typeof e.status !== "number") {
    return {
      fieldErrors,
      generalError:
        "Không kết nối được tới máy chủ. Kiểm tra lại kết nối mạng, " +
        "hoặc máy chủ chưa được khởi động.",
    };
  }

  if (typeof e.retry_after === "number") {
    const phut = Math.ceil(e.retry_after / 60);
    return {
      fieldErrors,
      generalError: `Bạn đã thử quá nhiều lần. Vui lòng chờ ${phut} phút rồi thử lại.`,
    };
  }

  const detail = e.detail;

  if (typeof detail === "string" && detail.trim()) {
    return { fieldErrors, generalError: detail };
  }

  if (Array.isArray(detail)) {
    for (const muc of detail) {
      if (typeof muc !== "object" || muc === null) {
        chung.push(String(muc));
        continue;
      }
      const m = muc as {
        field?: unknown;
        message?: unknown;
        loc?: unknown;
        msg?: unknown;
        type?: unknown;
      };

      // Dạng 2: tầng dịch vụ tự trả {field, message}.
      if (typeof m.field === "string" && typeof m.message === "string") {
        fieldErrors[m.field] = m.message;
        continue;
      }

      // Dạng 3: FastAPI trả {loc, msg, type}.
      if (typeof m.msg === "string") {
        const field = truongTuLoc(m.loc);
        const noiDung = dichThongBao(
          typeof m.type === "string" ? m.type : "",
          m.msg,
          field ?? "",
        );
        if (field) fieldErrors[field] = noiDung;
        else chung.push(noiDung);
        continue;
      }

      chung.push("Dữ liệu gửi lên không hợp lệ");
    }
  }

  // Không gắn được lỗi nào vào trường cụ thể thì BẮT BUỘC phải có lỗi chung,
  // nếu không form sẽ đứng im và người dùng không biết vì sao.
  if (!Object.keys(fieldErrors).length && !chung.length) {
    if (e.status >= 500) {
      chung.push("Máy chủ đang gặp sự cố. Vui lòng thử lại sau ít phút.");
    } else {
      chung.push("Đã xảy ra lỗi, vui lòng thử lại sau");
    }
  }

  return { fieldErrors, generalError: chung.join(" ") };
}
