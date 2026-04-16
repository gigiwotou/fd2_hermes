use minifb::{Key, Window, WindowOptions, MouseButton};
use std::fs::File;
use std::io::{Read, Write};

const SCREEN_WIDTH: usize = 900;
const SCREEN_HEIGHT: usize = 520;
const ANI_WIDTH: usize = 320;
const ANI_HEIGHT: usize = 200;
const BUFFER_SIZE: usize = ANI_WIDTH * ANI_HEIGHT;

// 动画名称
const ANIMATION_NAMES: &[&str] = &[
    "AFM 0 - Opening",
    "AFM 1 - Battle",
    "AFM 2 - Character",
    "AFM 3 - Effect",
    "AFM 4 - Item",
    "AFM 5 - Transition",
    "AFM 6 - Interface",
    "AFM 7 - Title",
    "AFM 8 - Ending",
];

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let ani_path = if args.len() > 1 {
        args[1].clone()
    } else {
        "../game/ANI.DAT".to_string()
    };

    // 读取 ANI.DAT
    let mut file = match File::open(&ani_path) {
        Ok(f) => f,
        Err(_) => {
            eprintln!("Cannot open file: {}", ani_path);
            return;
        }
    };

    let mut data = Vec::new();
    file.read_to_end(&mut data).unwrap();

    // 解析 AFM 索引
    let afm_offsets = parse_afm_index(&data);
    println!("Found {} AFM animations", afm_offsets.len());

    // 解码所有 AFM
    let mut all_animations: Vec<(Vec<Vec<u8>>, Vec<[u8; 768]>)> = Vec::new();
    
    for (idx, &offset) in afm_offsets.iter().enumerate() {
        let (frames, palettes) = decode_afm(&data, offset);
        let name = ANIMATION_NAMES.get(idx).unwrap_or(&"Unknown");
        println!("{}: {} frames", name, frames.len());
        all_animations.push((frames, palettes));
    }

    if all_animations.is_empty() {
        eprintln!("No animations found");
        return;
    }

    // 创建窗口
    let mut window = Window::new(
        "FD2 Animation Player - Click to select",
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        WindowOptions {
            scale: minifb::Scale::X1,
            ..WindowOptions::default()
        },
    )
    .unwrap();

    let mut current_afm = 0;
    let mut current_frame = 0;
    let mut frame_counter = 0;
    let mut buffer = vec![0u32; SCREEN_WIDTH * SCREEN_HEIGHT];
    let mut hovered_item: Option<usize> = None;
    let mut hovered_save_btn: Option<usize> = None;
    let mut status_message = String::new();
    let mut status_counter = 0u32;
    let mut last_click_time = 0u64;
    let mut click_count = 0;

    while window.is_open() && !window.is_key_down(Key::Escape) {
        // 获取鼠标位置
        let mouse_pos = window.get_mouse_pos(minifb::MouseMode::Clamp).unwrap_or((0.0, 0.0));
        let mx = mouse_pos.0 as usize;
        let my = mouse_pos.1 as usize;

        // 检测悬停项
        hovered_item = None;
        hovered_save_btn = None;
        
        let list_x = 10;
        let list_y = 40;
        let item_height = 28;
        
        for i in 0..all_animations.len().min(9) {
            let y = list_y + i * item_height;
            if mx >= list_x && mx < list_x + 200 && my >= y && my < y + item_height {
                hovered_item = Some(i);
            }
            let btn_x = list_x + 205;
            if mx >= btn_x && mx < btn_x + 60 && my >= y && my < y + item_height {
                hovered_save_btn = Some(i);
            }
        }

        // 处理鼠标点击
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;
        
        if window.get_mouse_down(MouseButton::Left) {
            if now - last_click_time < 300 {
                click_count += 1;
            } else {
                click_count = 1;
            }
            last_click_time = now;

            if click_count >= 2 {
                if let Some(idx) = hovered_item {
                    current_afm = idx;
                    current_frame = 0;
                    frame_counter = 0;
                    status_message = format!("Selected: {}", ANIMATION_NAMES.get(idx).unwrap_or(&"Unknown"));
                    status_counter = 60;
                }
            }
            
            if let Some(idx) = hovered_save_btn {
                if idx < all_animations.len() {
                    let name = ANIMATION_NAMES.get(idx).unwrap_or(&"unknown");
                    let filename = format!("{}.gif", name.split(" - ").next().unwrap_or("animation"));
                    match save_animation_as_gif(&all_animations[idx], &filename) {
                        Ok(_) => {
                            status_message = format!("Saved: {}", filename);
                            status_counter = 120;
                        }
                        Err(e) => {
                            status_message = format!("Save failed: {}", e);
                            status_counter = 120;
                        }
                    }
                }
            }
        }

        // 键盘控制
        if window.is_key_pressed(Key::Left, minifb::KeyRepeat::No) {
            if current_afm > 0 {
                current_afm -= 1;
                current_frame = 0;
                frame_counter = 0;
            }
        }
        if window.is_key_pressed(Key::Right, minifb::KeyRepeat::No) {
            if current_afm < all_animations.len() - 1 {
                current_afm += 1;
                current_frame = 0;
                frame_counter = 0;
            }
        }

        let num_keys = [Key::Key1, Key::Key2, Key::Key3, Key::Key4, Key::Key5,
                       Key::Key6, Key::Key7, Key::Key8, Key::Key9];
        for (i, &key) in num_keys.iter().enumerate() {
            if window.is_key_pressed(key, minifb::KeyRepeat::No) {
                if i < all_animations.len() {
                    current_afm = i;
                    current_frame = 0;
                    frame_counter = 0;
                }
            }
        }

        if window.is_key_pressed(Key::S, minifb::KeyRepeat::No) {
            let name = ANIMATION_NAMES.get(current_afm).unwrap_or(&"animation");
            let filename = format!("{}.gif", name.split(" - ").next().unwrap_or("animation"));
            match save_animation_as_gif(&all_animations[current_afm], &filename) {
                Ok(_) => {
                    status_message = format!("Saved: {}", filename);
                    status_counter = 120;
                }
                Err(e) => {
                    status_message = format!("Save failed: {}", e);
                    status_counter = 120;
                }
            }
        }

        if status_counter > 0 {
            status_counter -= 1;
        }

        // 播放动画
        let (frames, palettes) = &all_animations[current_afm];
        if !frames.is_empty() {
            frame_counter += 1;
            if frame_counter >= 3 {
                frame_counter = 0;
                current_frame = (current_frame + 1) % frames.len();
            }
        }

        // 绘制UI
        draw_ui(
            &mut buffer,
            current_afm,
            current_frame,
            frames.len(),
            hovered_item,
            hovered_save_btn,
            &status_message,
            status_counter > 0,
            &frames[current_frame],
            &palettes[current_frame],
        );

        window.update_with_buffer(&buffer, SCREEN_WIDTH, SCREEN_HEIGHT).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(33));
    }
}

fn draw_ui(
    buffer: &mut [u32],
    current_afm: usize,
    current_frame: usize,
    total_frames: usize,
    hovered_item: Option<usize>,
    hovered_save_btn: Option<usize>,
    status_message: &str,
    show_status: bool,
    frame_data: &[u8],
    palette: &[u8; 768],
) {
    // 清空背景
    for pixel in buffer.iter_mut() {
        *pixel = 0x303030;
    }

    // 绘制标题
    draw_text(buffer, "FD2 Animation Player", 10, 10, 0xFFFFFF);
    draw_text(buffer, "Double-click select | S=Save | ESC=Exit", 10, 25, 0xAAAAAA);

    // 绘制动画列表
    let list_x = 10;
    let list_y = 40;
    let item_height = 28;

    for i in 0..ANIMATION_NAMES.len().min(9) {
        let y = list_y + i * item_height;
        let is_selected = i == current_afm;
        let is_hovered = hovered_item == Some(i);
        let is_save_hovered = hovered_save_btn == Some(i);

        let bg_color = if is_selected {
            0x004488
        } else if is_hovered {
            0x444444
        } else {
            0x383838
        };
        fill_rect(buffer, list_x, y, 200, item_height - 2, bg_color);

        let text_color = if is_selected { 0xFFFFFF } else { 0xCCCCCC };
        draw_text(buffer, ANIMATION_NAMES[i], list_x + 5, y + 8, text_color);

        let btn_x = list_x + 205;
        let btn_color = if is_save_hovered { 0x00AA00 } else { 0x006600 };
        fill_rect(buffer, btn_x, y, 60, item_height - 2, btn_color);
        draw_text(buffer, "Save", btn_x + 15, y + 8, 0xFFFFFF);
    }

    // 绘制动画预览区域
    let preview_x = 290;
    let preview_y = 40;
    let preview_scale = 2;

    fill_rect(buffer, preview_x, preview_y, ANI_WIDTH * preview_scale, ANI_HEIGHT * preview_scale, 0x000000);
    draw_frame_scaled(buffer, preview_x, preview_y, frame_data, palette, preview_scale);
    draw_text(buffer, &format!("Frame: {}/{}", current_frame + 1, total_frames), preview_x, preview_y + ANI_HEIGHT * preview_scale + 10, 0xFFFFFF);

    // 状态消息
    if show_status && !status_message.is_empty() {
        let msg_width = status_message.len() * 8;
        let msg_x = (SCREEN_WIDTH - msg_width) / 2;
        let msg_y = SCREEN_HEIGHT - 40;
        fill_rect(buffer, msg_x - 10, msg_y - 5, msg_width + 20, 25, 0x006600);
        draw_text(buffer, status_message, msg_x, msg_y, 0xFFFFFF);
    }
}

fn draw_frame_scaled(
    buffer: &mut [u32],
    offset_x: usize,
    offset_y: usize,
    frame_data: &[u8],
    palette: &[u8; 768],
    scale: usize,
) {
    for y in 0..ANI_HEIGHT {
        for x in 0..ANI_WIDTH {
            let pixel = frame_data[y * ANI_WIDTH + x];
            let idx = pixel as usize * 3;
            let r = (palette[idx] as u32 * 4).min(255);
            let g = (palette[idx + 1] as u32 * 4).min(255);
            let b = (palette[idx + 2] as u32 * 4).min(255);
            let color = (r << 16) | (g << 8) | b;

            for sy in 0..scale {
                for sx in 0..scale {
                    let px = offset_x + x * scale + sx;
                    let py = offset_y + y * scale + sy;
                    if px < SCREEN_WIDTH && py < SCREEN_HEIGHT {
                        buffer[py * SCREEN_WIDTH + px] = color;
                    }
                }
            }
        }
    }
}

fn fill_rect(buffer: &mut [u32], x: usize, y: usize, w: usize, h: usize, color: u32) {
    for py in y..y.saturating_add(h).min(SCREEN_HEIGHT) {
        for px in x..x.saturating_add(w).min(SCREEN_WIDTH) {
            buffer[py * SCREEN_WIDTH + px] = color;
        }
    }
}

// 简单位图字体数据 (8x8)
static FONT: [[u8; 8]; 128] = {
    let mut font = [[0u8; 8]; 128];
    // 空格
    font[32] = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00];
    // 数字 0-9
    font[48] = [0x3C, 0x42, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00];
    font[49] = [0x08, 0x18, 0x28, 0x08, 0x08, 0x08, 0x3E, 0x00];
    font[50] = [0x3C, 0x42, 0x02, 0x0C, 0x30, 0x40, 0x7E, 0x00];
    font[51] = [0x3C, 0x42, 0x02, 0x1C, 0x02, 0x42, 0x3C, 0x00];
    font[52] = [0x04, 0x0C, 0x14, 0x24, 0x7E, 0x04, 0x04, 0x00];
    font[53] = [0x7E, 0x40, 0x7C, 0x02, 0x02, 0x42, 0x3C, 0x00];
    font[54] = [0x1C, 0x20, 0x40, 0x7C, 0x42, 0x42, 0x3C, 0x00];
    font[55] = [0x7E, 0x02, 0x04, 0x08, 0x10, 0x10, 0x10, 0x00];
    font[56] = [0x3C, 0x42, 0x42, 0x3C, 0x42, 0x42, 0x3C, 0x00];
    font[57] = [0x3C, 0x42, 0x42, 0x3E, 0x02, 0x04, 0x38, 0x00];
    // A-Z
    font[65] = [0x10, 0x28, 0x44, 0x44, 0x7C, 0x44, 0x44, 0x00];
    font[66] = [0x78, 0x44, 0x44, 0x78, 0x44, 0x44, 0x78, 0x00];
    font[67] = [0x3C, 0x44, 0x40, 0x40, 0x40, 0x44, 0x3C, 0x00];
    font[68] = [0x78, 0x44, 0x44, 0x44, 0x44, 0x44, 0x78, 0x00];
    font[69] = [0x7C, 0x40, 0x40, 0x78, 0x40, 0x40, 0x7C, 0x00];
    font[70] = [0x7C, 0x40, 0x40, 0x78, 0x40, 0x40, 0x40, 0x00];
    font[71] = [0x3C, 0x44, 0x40, 0x4E, 0x44, 0x44, 0x3E, 0x00];
    font[72] = [0x44, 0x44, 0x44, 0x7C, 0x44, 0x44, 0x44, 0x00];
    font[73] = [0x38, 0x10, 0x10, 0x10, 0x10, 0x10, 0x38, 0x00];
    font[74] = [0x04, 0x04, 0x04, 0x04, 0x04, 0x44, 0x38, 0x00];
    font[75] = [0x44, 0x48, 0x50, 0x60, 0x50, 0x48, 0x44, 0x00];
    font[76] = [0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x7C, 0x00];
    font[77] = [0x44, 0x6C, 0x54, 0x44, 0x44, 0x44, 0x44, 0x00];
    font[78] = [0x44, 0x64, 0x54, 0x4C, 0x44, 0x44, 0x44, 0x00];
    font[79] = [0x38, 0x44, 0x44, 0x44, 0x44, 0x44, 0x38, 0x00];
    font[80] = [0x78, 0x44, 0x44, 0x78, 0x40, 0x40, 0x40, 0x00];
    font[81] = [0x38, 0x44, 0x44, 0x44, 0x54, 0x48, 0x34, 0x00];
    font[82] = [0x78, 0x44, 0x44, 0x78, 0x48, 0x44, 0x44, 0x00];
    font[83] = [0x3C, 0x44, 0x40, 0x3C, 0x04, 0x44, 0x3C, 0x00];
    font[84] = [0x7C, 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x00];
    font[85] = [0x44, 0x44, 0x44, 0x44, 0x44, 0x44, 0x38, 0x00];
    font[86] = [0x44, 0x44, 0x44, 0x44, 0x44, 0x28, 0x10, 0x00];
    font[87] = [0x44, 0x44, 0x44, 0x54, 0x54, 0x6C, 0x44, 0x00];
    font[88] = [0x44, 0x28, 0x10, 0x10, 0x10, 0x28, 0x44, 0x00];
    font[89] = [0x44, 0x44, 0x28, 0x10, 0x10, 0x10, 0x10, 0x00];
    font[90] = [0x7C, 0x04, 0x08, 0x10, 0x20, 0x40, 0x7C, 0x00];
    // 特殊字符
    font[45] = [0x00, 0x00, 0x00, 0x7C, 0x00, 0x00, 0x00, 0x00];
    font[47] = [0x04, 0x08, 0x08, 0x10, 0x10, 0x20, 0x20, 0x00];
    font[58] = [0x00, 0x00, 0x10, 0x00, 0x00, 0x10, 0x00, 0x00];
    font[97] = [0x00, 0x00, 0x3C, 0x04, 0x3C, 0x44, 0x3C, 0x00]; // a
    font[101] = [0x00, 0x00, 0x3C, 0x44, 0x7C, 0x40, 0x3C, 0x00]; // e
    font[105] = [0x00, 0x10, 0x00, 0x10, 0x10, 0x10, 0x10, 0x00]; // i
    font[111] = [0x00, 0x00, 0x3C, 0x44, 0x44, 0x44, 0x3C, 0x00]; // o
    font[117] = [0x00, 0x00, 0x44, 0x44, 0x44, 0x44, 0x3C, 0x00]; // u
    font[118] = [0x00, 0x00, 0x44, 0x44, 0x44, 0x28, 0x10, 0x00]; // v
    font[100] = [0x04, 0x04, 0x3C, 0x44, 0x44, 0x44, 0x3C, 0x00]; // d
    font[110] = [0x00, 0x00, 0x5C, 0x62, 0x42, 0x42, 0x42, 0x00]; // n
    font[115] = [0x00, 0x00, 0x3C, 0x40, 0x3C, 0x04, 0x3C, 0x00]; // s
    font[116] = [0x10, 0x10, 0x38, 0x10, 0x10, 0x10, 0x08, 0x00]; // t
    font[108] = [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x00]; // l
    font[99] = [0x00, 0x00, 0x3C, 0x40, 0x40, 0x40, 0x3C, 0x00]; // c
    font[114] = [0x00, 0x00, 0x5C, 0x60, 0x40, 0x40, 0x40, 0x00]; // r
    font[102] = [0x08, 0x10, 0x38, 0x10, 0x10, 0x10, 0x08, 0x00]; // f
    font[109] = [0x00, 0x00, 0x76, 0x49, 0x49, 0x49, 0x49, 0x00]; // m
    font[112] = [0x00, 0x00, 0x78, 0x44, 0x44, 0x44, 0x78, 0x40]; // p
    font[98] = [0x00, 0x00, 0x78, 0x44, 0x44, 0x44, 0x78, 0x00]; // b
    font[103] = [0x00, 0x00, 0x3C, 0x44, 0x44, 0x3C, 0x04, 0x00]; // g
    font[104] = [0x40, 0x40, 0x5C, 0x62, 0x42, 0x42, 0x42, 0x00]; // h
    font[107] = [0x40, 0x40, 0x4C, 0x50, 0x48, 0x44, 0x40, 0x00]; // k
    font[119] = [0x00, 0x00, 0x44, 0x6C, 0x54, 0x44, 0x44, 0x00]; // w
    font[120] = [0x00, 0x00, 0x44, 0x28, 0x10, 0x28, 0x44, 0x00]; // x
    font[121] = [0x00, 0x00, 0x44, 0x28, 0x10, 0x10, 0x10, 0x00]; // y
    font[122] = [0x00, 0x00, 0x7C, 0x08, 0x10, 0x20, 0x7C, 0x00]; // z
    font
};

fn draw_text(buffer: &mut [u32], text: &str, x: usize, y: usize, color: u32) {
    let mut cx = x;
    for ch in text.chars() {
        let code = ch as usize;
        if code < 128 {
            let glyph = FONT[code];
            for (row, &bits) in glyph.iter().enumerate() {
                for col in 0..8 {
                    if (bits & (0x80 >> col)) != 0 {
                        let px = cx + col;
                        let py = y + row;
                        if px < SCREEN_WIDTH && py < SCREEN_HEIGHT {
                            buffer[py * SCREEN_WIDTH + px] = color;
                        }
                    }
                }
            }
        }
        cx += 8;
    }
}

fn save_animation_as_gif(animation: &(Vec<Vec<u8>>, Vec<[u8; 768]>), filename: &str) -> std::io::Result<()> {
    let (frames, palettes) = animation;
    if frames.is_empty() {
        return Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "No frames"));
    }

    let mut file = File::create(filename)?;
    
    // GIF89a header
    file.write_all(b"GIF89a")?;
    
    // Logical Screen Descriptor
    file.write_all(&(ANI_WIDTH as u16).to_le_bytes())?;
    file.write_all(&(ANI_HEIGHT as u16).to_le_bytes())?;
    file.write_all(&[0xF7])?;
    file.write_all(&[0])?;
    file.write_all(&[0])?;

    // Global Color Table
    for i in 0..256 {
        let idx = i * 3;
        let r = (palettes[0][idx] as u8).wrapping_mul(4).min(255);
        let g = (palettes[0][idx + 1] as u8).wrapping_mul(4).min(255);
        let b = (palettes[0][idx + 2] as u8).wrapping_mul(4).min(255);
        file.write_all(&[r, g, b])?;
    }

    // Netscape Extension
    file.write_all(&[0x21, 0xFF, 0x0B])?;
    file.write_all(b"NETSCAPE2.0")?;
    file.write_all(&[0x03, 0x01, 0x00, 0x00, 0x00])?;

    let frame_delay = 10u16;

    for frame in frames.iter() {
        // Graphic Control Extension
        file.write_all(&[0x21, 0xF9, 0x04])?;
        file.write_all(&[0x04])?;
        file.write_all(&frame_delay.to_le_bytes())?;
        file.write_all(&[0x00, 0x00])?;

        // Image Descriptor
        file.write_all(&[0x2C])?;
        file.write_all(&[0u8; 8])?;
        
        // LZW Minimum Code Size
        file.write_all(&[8])?;

        // LZW encode
        let compressed = lzw_encode(frame);
        
        let mut pos = 0;
        while pos < compressed.len() {
            let chunk_size = std::cmp::min(255, compressed.len() - pos);
            file.write_all(&[chunk_size as u8])?;
            file.write_all(&compressed[pos..pos + chunk_size])?;
            pos += chunk_size;
        }
        file.write_all(&[0x00])?;
    }

    file.write_all(&[0x3B])?;
    Ok(())
}

// LZW 编码器状态
struct LzwEncoder {
    bit_buffer: u32,
    bit_count: u8,
    output: Vec<u8>,
    code_size: u8,
    next_code: u16,
    max_code: u16,
    clear_code: u16,
    end_code: u16,
}

impl LzwEncoder {
    fn new() -> Self {
        LzwEncoder {
            bit_buffer: 0,
            bit_count: 0,
            output: Vec::new(),
            code_size: 9,
            next_code: 258,
            max_code: 511,
            clear_code: 256,
            end_code: 257,
        }
    }

    fn write_code(&mut self, code: u16) {
        self.bit_buffer |= (code as u32) << self.bit_count;
        self.bit_count += self.code_size;
        
        while self.bit_count >= 8 {
            self.output.push((self.bit_buffer & 0xFF) as u8);
            self.bit_buffer >>= 8;
            self.bit_count -= 8;
        }
    }

    fn flush(&mut self) {
        if self.bit_count > 0 {
            self.output.push((self.bit_buffer & 0xFF) as u8);
        }
    }

    fn bump_code_size(&mut self) {
        if self.next_code > self.max_code && self.code_size < 12 {
            self.code_size += 1;
            self.max_code = (1 << self.code_size) - 1;
        }
    }
}

fn lzw_encode(data: &[u8]) -> Vec<u8> {
    use std::collections::HashMap;
    
    let mut encoder = LzwEncoder::new();
    let mut code_table: HashMap<Vec<u8>, u16> = HashMap::new();
    
    for i in 0..256 {
        code_table.insert(vec![i as u8], i as u16);
    }
    
    encoder.write_code(encoder.clear_code);
    
    if data.is_empty() {
        encoder.write_code(encoder.end_code);
        encoder.flush();
        return encoder.output;
    }
    
    let mut buffer = vec![data[0]];
    
    for &byte in &data[1..] {
        let mut test_buffer = buffer.clone();
        test_buffer.push(byte);
        
        if code_table.contains_key(&test_buffer) {
            buffer = test_buffer;
        } else {
            if let Some(&code) = code_table.get(&buffer) {
                encoder.write_code(code);
            }
            
            if encoder.next_code < 4096 {
                code_table.insert(test_buffer, encoder.next_code);
                encoder.next_code += 1;
                encoder.bump_code_size();
            }
            
            buffer = vec![byte];
        }
    }
    
    if let Some(&code) = code_table.get(&buffer) {
        encoder.write_code(code);
    }
    
    encoder.write_code(encoder.end_code);
    encoder.flush();
    
    encoder.output
}

fn parse_afm_index(data: &[u8]) -> Vec<usize> {
    let mut offsets = Vec::new();
    let mut pos = 6;

    while pos + 4 <= data.len() {
        let offset = u32::from_le_bytes([data[pos], data[pos + 1], data[pos + 2], data[pos + 3]]) as usize;
        if offset == 0 {
            break;
        }

        if offset + 167 < data.len() {
            let frame_count = u16::from_le_bytes([data[offset + 165], data[offset + 166]]) as usize;
            if frame_count > 0 && frame_count < 1000 {
                offsets.push(offset);
            }
        }

        pos += 4;
        if offsets.len() > 20 {
            break;
        }
    }

    offsets
}

fn decode_afm(data: &[u8], afm_offset: usize) -> (Vec<Vec<u8>>, Vec<[u8; 768]>) {
    let frame_count = u16::from_le_bytes([data[afm_offset + 165], data[afm_offset + 166]]) as usize;
    let frame_start = afm_offset + 173;

    let mut palette_buf = [0u8; 768];
    let mut pixel_buf = [0u8; BUFFER_SIZE];
    let mut frames = Vec::new();
    let mut palettes = Vec::new();
    let mut prev_pixel_buf = [0u8; BUFFER_SIZE];

    let mut pos = frame_start;

    for _ in 0..frame_count {
        if pos + 8 > data.len() {
            break;
        }

        let size = u16::from_le_bytes([data[pos], data[pos + 1]]) as usize;
        let param = u16::from_le_bytes([data[pos + 2], data[pos + 3]]) as usize;

        let frame_data = if size > 0 && pos + 8 + size <= data.len() {
            &data[pos + 8..pos + 8 + size]
        } else {
            &[]
        };

        prev_pixel_buf.copy_from_slice(&pixel_buf);
        process_frame(param, frame_data, &mut palette_buf, &mut pixel_buf);

        pos += 8 + size;

        if pixel_buf != prev_pixel_buf {
            frames.push(pixel_buf.to_vec());
            palettes.push(palette_buf);
        }
    }

    (frames, palettes)
}

fn process_frame(
    param: usize,
    frame_data: &[u8],
    palette_buf: &mut [u8],
    pixel_buf: &mut [u8],
) {
    if param == 0 || frame_data.is_empty() {
        return;
    }

    let mut data_pos = 0;

    for _ in 0..param {
        if data_pos >= frame_data.len() {
            break;
        }

        let cmd = frame_data[data_pos];
        data_pos += 1;

        match cmd {
            0x00 => {
                if data_pos < frame_data.len() {
                    let color = frame_data[data_pos];
                    data_pos += 1;
                    for i in 0..256 {
                        palette_buf[i * 3] = color;
                        palette_buf[i * 3 + 1] = color;
                        palette_buf[i * 3 + 2] = color;
                    }
                }
            }
            0x01 => {
                if data_pos + 768 <= frame_data.len() {
                    palette_buf.copy_from_slice(&frame_data[data_pos..data_pos + 768]);
                    data_pos += 768;
                }
            }
            0x02 => {
                let mut src_pos = data_pos;
                let mut dst_pos = 0;
                while dst_pos < 768 && src_pos < frame_data.len() {
                    let b = frame_data[src_pos];
                    src_pos += 1;
                    if (b & 0xC0) == 0xC0 {
                        let count = (b & 0x3F) as usize;
                        if src_pos < frame_data.len() {
                            let color = frame_data[src_pos];
                            src_pos += 1;
                            for i in 0..count.min(768 - dst_pos) {
                                palette_buf[dst_pos + i] = color;
                            }
                            dst_pos += count;
                        }
                    } else {
                        palette_buf[dst_pos] = b;
                        dst_pos += 1;
                    }
                }
                data_pos = src_pos;
            }
            0x04 => {
                if data_pos < frame_data.len() {
                    let fill_byte = frame_data[data_pos];
                    data_pos += 1;
                    for i in 0..BUFFER_SIZE {
                        pixel_buf[i] = fill_byte;
                    }
                }
            }
            0x05 => {
                if data_pos + BUFFER_SIZE <= frame_data.len() {
                    pixel_buf.copy_from_slice(&frame_data[data_pos..data_pos + BUFFER_SIZE]);
                    data_pos += BUFFER_SIZE;
                }
            }
            0x06 => {
                let (consumed, _) = decode_rle(&frame_data[data_pos..], pixel_buf);
                data_pos += consumed;
            }
            0x07 => {
                if data_pos + 2 <= frame_data.len() {
                    let count = u16::from_le_bytes([frame_data[data_pos], frame_data[data_pos + 1]]) as usize;
                    data_pos += 2;

                    for _ in 0..count {
                        if data_pos + 3 > frame_data.len() {
                            break;
                        }
                        let offset = u16::from_le_bytes([frame_data[data_pos], frame_data[data_pos + 1]]) as usize;
                        let color = frame_data[data_pos + 2];
                        data_pos += 3;

                        if offset < BUFFER_SIZE {
                            pixel_buf[offset] = color;
                        }
                    }
                }
            }
            0x08 => {
                if data_pos + 2 <= frame_data.len() {
                    let count = u16::from_le_bytes([frame_data[data_pos], frame_data[data_pos + 1]]) as usize;
                    data_pos += 2;

                    for _ in 0..count {
                        if data_pos + 4 > frame_data.len() {
                            break;
                        }
                        let offset = u16::from_le_bytes([frame_data[data_pos], frame_data[data_pos + 1]]) as usize;
                        let size = frame_data[data_pos + 2] as usize;
                        let color = frame_data[data_pos + 3];
                        data_pos += 4;

                        for i in 0..size.min(BUFFER_SIZE - offset) {
                            pixel_buf[offset + i] = color;
                        }
                    }
                }
            }
            0x09 => {
                if data_pos + 2 <= frame_data.len() {
                    let count = u16::from_le_bytes([frame_data[data_pos], frame_data[data_pos + 1]]) as usize;
                    data_pos += 2;

                    for _ in 0..count {
                        if data_pos + 3 > frame_data.len() {
                            break;
                        }
                        let dst = u16::from_le_bytes([frame_data[data_pos], frame_data[data_pos + 1]]) as usize;
                        let size = frame_data[data_pos + 2] as usize;
                        data_pos += 3;

                        for i in 0..size.min(BUFFER_SIZE - dst) {
                            if data_pos + i < frame_data.len() {
                                pixel_buf[dst + i] = frame_data[data_pos + i];
                            }
                        }
                        data_pos += size;
                    }
                }
            }
            _ => break,
        }
    }
}

fn decode_rle(data: &[u8], pixel_buf: &mut [u8]) -> (usize, usize) {
    let mut src_pos = 0;
    let mut dst_pos = 0;

    while src_pos < data.len() && dst_pos < BUFFER_SIZE {
        let b = data[src_pos];
        src_pos += 1;

        if (b & 0xC0) == 0xC0 {
            let count = (b & 0x3F) as usize;
            if src_pos < data.len() {
                let color = data[src_pos];
                src_pos += 1;
                for i in 0..count.min(BUFFER_SIZE - dst_pos) {
                    pixel_buf[dst_pos + i] = color;
                }
                dst_pos += count;
            }
        } else {
            if dst_pos < BUFFER_SIZE {
                pixel_buf[dst_pos] = b;
            }
            dst_pos += 1;
        }
    }

    (src_pos, dst_pos)
}
