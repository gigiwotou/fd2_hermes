use minifb::{Key, Window, WindowOptions, Scale};
use std::fs::File;
use std::io::Read;

// 游戏原始分辨率
const ANI_WIDTH: usize = 320;
const ANI_HEIGHT: usize = 200;
const BUFFER_SIZE: usize = ANI_WIDTH * ANI_HEIGHT;

// UI 布局
const LIST_WIDTH: usize = 100;  // 播放列表宽度（像素，会随 scale 放大）
const LIST_X: usize = ANI_WIDTH;  // 播放列表起始位置

const ANIMATION_NAMES: &[&str] = &[
    "0:Opening",
    "1:Battle",
    "2:Character",
    "3:Effect",
    "4:Item",
    "5:Transition",
    "6:Interface",
    "7:Title",
    "8:Ending",
];

fn main() {
    let args: Vec<String> = std::env::args().collect();
    
    // 解析缩放参数
    let scale_arg = args.iter().find(|a| a.starts_with("--scale=") || a.starts_with("-s="));
    let scale = match scale_arg {
        Some(arg) => {
            let val = arg.split('=').nth(1).unwrap_or("2");
            match val {
                "1" => Scale::X1,
                "2" => Scale::X2,
                "4" => Scale::X4,
                "f" | "fit" => Scale::FitScreen,
                _ => Scale::X2,
            }
        }
        None => Scale::X2,
    };

    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("FD2 Animation Player");
        println!();
        println!("Usage: fd2_player [ANI.DAT] [OPTIONS]");
        println!();
        println!("Options:");
        println!("  -s=N, --scale=N  Set scale: 1, 2, 4, or fit");
        println!("                    1 = 320x200 (original)");
        println!("                    2 = 640x400 (default)");
        println!("                    4 = 1280x800");
        println!("                    fit = auto-fit to screen");
        println!("  -h, --help        Show this help");
        println!();
        println!("Controls:");
        println!("  1-9        Select animation");
        println!("  Left/Right Navigate");
        println!("  S          Save as GIF");
        println!("  ESC        Exit");
        return;
    }

    let ani_path = if args.len() > 1 && !args[1].starts_with('-') {
        args[1].clone()
    } else {
        if std::path::Path::new("ANI.DAT").exists() {
            "ANI.DAT".to_string()
        } else {
            eprintln!("Error: ANI.DAT not found!");
            eprintln!("Usage: fd2_player [ANI.DAT path] [--scale=1|2|4|fit]");
            return;
        }
    };

    eprintln!("Loading: {}", ani_path);
    eprintln!("Scale: {:?}", scale);

    let mut file = match File::open(&ani_path) {
        Ok(f) => f,
        Err(_) => {
            eprintln!("Cannot open file: {}", ani_path);
            return;
        }
    };

    let mut data = Vec::new();
    file.read_to_end(&mut data).unwrap();

    let afm_offsets = parse_afm_index(&data);
    println!("Found {} AFM animations", afm_offsets.len());

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

    // 窗口宽度 = 动画宽度 + 列表宽度
    let window_width = ANI_WIDTH + LIST_WIDTH;
    let window_height = ANI_HEIGHT;

    let mut window = Window::new(
        "FD2 Player",
        window_width,
        window_height,
        WindowOptions {
            scale: scale,
            resize: true,
            ..WindowOptions::default()
        },
    )
    .unwrap();

    let mut current_afm = 0;
    let mut current_frame = 0;
    let mut frame_counter = 0;
    // 窗口缓冲区包含动画+列表区域
    let buffer_size = window_width * window_height;
    let mut buffer = vec![0u32; buffer_size];
    let mut status_message = String::new();
    let mut status_counter = 0u32;

    println!("\nControls:");
    println!("  [1-9]        : Select animation");
    println!("  [Left/Right] : Navigate");
    println!("  [S]          : Save as GIF");
    println!("  [ESC]        : Exit");

    while window.is_open() && !window.is_key_down(Key::Escape) {
        // 动画选择
        let num_keys = [Key::Key1, Key::Key2, Key::Key3, Key::Key4, Key::Key5,
                       Key::Key6, Key::Key7, Key::Key8, Key::Key9];
        for (i, &key) in num_keys.iter().enumerate() {
            if window.is_key_pressed(key, minifb::KeyRepeat::No) {
                if i < all_animations.len() {
                    current_afm = i;
                    current_frame = 0;
                    frame_counter = 0;
                    status_message = format!("Selected: {}", ANIMATION_NAMES[i]);
                    status_counter = 60;
                }
            }
        }

        // 左右切换
        if window.is_key_pressed(Key::Left, minifb::KeyRepeat::No) {
            if current_afm > 0 {
                current_afm -= 1;
                current_frame = 0;
                frame_counter = 0;
                status_message = format!("Selected: {}", ANIMATION_NAMES[current_afm]);
                status_counter = 60;
            }
        }
        if window.is_key_pressed(Key::Right, minifb::KeyRepeat::No) {
            if current_afm < all_animations.len() - 1 {
                current_afm += 1;
                current_frame = 0;
                frame_counter = 0;
                status_message = format!("Selected: {}", ANIMATION_NAMES[current_afm]);
                status_counter = 60;
            }
        }

        // 保存GIF
        if window.is_key_pressed(Key::S, minifb::KeyRepeat::No) {
            let name = ANIMATION_NAMES.get(current_afm).unwrap_or(&"animation");
            let filename = format!("AFM_{}.gif", name.split(':').next().unwrap_or("0"));
            match save_animation_as_gif(&all_animations[current_afm], &filename) {
                Ok(_) => {
                    status_message = format!("Saved: {}", filename);
                    status_counter = 120;
                    println!("Saved: {}", filename);
                }
                Err(e) => {
                    status_message = format!("Error: {}", e);
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

            // 更新标题
            let title = format!(
                "{} | Frame {}/{} | [ESC] Exit",
                ANIMATION_NAMES[current_afm],
                current_frame + 1,
                frames.len()
            );
            window.set_title(&title);

            // 清空缓冲区
            for pixel in buffer.iter_mut() {
                *pixel = 0x222222;
            }

            // 绘制动画帧（左侧）
            render_frame_to_buffer(&mut buffer, window_width, window_height,
                                   &frames[current_frame], &palettes[current_frame]);

            // 绘制播放列表（右侧）
            draw_playlist(&mut buffer, window_width, window_height, current_afm, all_animations.len());

            // 绘制状态栏
            if status_counter > 0 && !status_message.is_empty() {
                draw_status_bar(&mut buffer, window_width, window_height, &status_message);
            }

            window.update_with_buffer(&buffer, window_width, window_height).unwrap();
        } else {
            window.update();
        }

        std::thread::sleep(std::time::Duration::from_millis(33));
    }
}

fn render_frame_to_buffer(
    buffer: &mut [u32],
    buf_width: usize,
    _buf_height: usize,
    frame_data: &[u8],
    palette: &[u8; 768],
) {
    for y in 0..ANI_HEIGHT {
        for x in 0..ANI_WIDTH {
            let pixel = frame_data[y * ANI_WIDTH + x];
            let idx = pixel as usize * 3;
            let r = (palette[idx] as u32 * 4).min(255);
            let g = (palette[idx + 1] as u32 * 4).min(255);
            let b = (palette[idx + 2] as u32 * 4).min(255);
            let color = (r << 16) | (g << 8) | b;
            buffer[y * buf_width + x] = color;
        }
    }
}

fn draw_playlist(buffer: &mut [u32], buf_width: usize, buf_height: usize, selected: usize, total: usize) {
    let list_x = ANI_WIDTH;
    let item_height = 20;
    let padding = 2;

    // 标题
    draw_text(buffer, buf_width, buf_height, "Playlist", list_x + 4, 4, 0xFFFFFF);

    // 分隔线
    for x in list_x..buf_width {
        buffer[14 * buf_width + x] = 0x555555;
    }

    // 动画列表
    for i in 0..total.min(9) {
        let y = 18 + i * item_height;
        
        // 选中项背景
        if i == selected {
            for dy in 0..item_height {
                for dx in 0..LIST_WIDTH {
                    let py = y + dy;
                    let px = list_x + dx;
                    if py < buf_height && px < buf_width {
                        buffer[py * buf_width + px] = 0x004488;
                    }
                }
            }
        }

        // 动画名称
        let color = if i == selected { 0xFFFF00 } else { 0xAAAAAA };
        draw_text(buffer, buf_width, buf_height, ANIMATION_NAMES[i], list_x + 4, y + 4, color);
    }

    // 保存提示
    let save_y = buf_height - 20;
    draw_text(buffer, buf_width, buf_height, "[S] Save GIF", list_x + 4, save_y, 0x00CC00);
}

fn draw_status_bar(buffer: &mut [u32], buf_width: usize, buf_height: usize, message: &str) {
    let bar_height = 16;
    let y_start = ANI_HEIGHT - bar_height;

    // 背景
    for y in y_start..ANI_HEIGHT.min(buf_height) {
        for x in 0..ANI_WIDTH.min(buf_width) {
            buffer[y * buf_width + x] = 0x003300;
        }
    }

    // 文本
    draw_text(buffer, buf_width, buf_height, message, 4, y_start + 4, 0xFFFFFF);
}

fn draw_text(buffer: &mut [u32], buf_width: usize, buf_height: usize, text: &str, x: usize, y: usize, color: u32) {
    static FONT: [[u8; 8]; 128] = {
        let mut font = [[0u8; 8]; 128];
        // 数字
        font[48] = [0x3C, 0x42, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00]; // 0
        font[49] = [0x08, 0x18, 0x28, 0x08, 0x08, 0x08, 0x3E, 0x00]; // 1
        font[50] = [0x3C, 0x42, 0x02, 0x0C, 0x30, 0x40, 0x7E, 0x00]; // 2
        font[51] = [0x3C, 0x42, 0x02, 0x1C, 0x02, 0x42, 0x3C, 0x00]; // 3
        font[52] = [0x04, 0x0C, 0x14, 0x24, 0x7E, 0x04, 0x04, 0x00]; // 4
        font[53] = [0x7E, 0x40, 0x7C, 0x02, 0x02, 0x42, 0x3C, 0x00]; // 5
        font[54] = [0x1C, 0x20, 0x40, 0x7C, 0x42, 0x42, 0x3C, 0x00]; // 6
        font[55] = [0x7E, 0x02, 0x04, 0x08, 0x10, 0x10, 0x10, 0x00]; // 7
        font[56] = [0x3C, 0x42, 0x42, 0x3C, 0x42, 0x42, 0x3C, 0x00]; // 8
        font[57] = [0x3C, 0x42, 0x42, 0x3E, 0x02, 0x04, 0x38, 0x00]; // 9
        // 字母
        font[65] = [0x10, 0x28, 0x44, 0x44, 0x7C, 0x44, 0x44, 0x00]; // A
        font[66] = [0x78, 0x44, 0x44, 0x78, 0x44, 0x44, 0x78, 0x00]; // B
        font[67] = [0x3C, 0x44, 0x40, 0x40, 0x40, 0x44, 0x3C, 0x00]; // C
        font[68] = [0x78, 0x44, 0x44, 0x44, 0x44, 0x44, 0x78, 0x00]; // D
        font[69] = [0x7C, 0x40, 0x40, 0x78, 0x40, 0x40, 0x7C, 0x00]; // E
        font[70] = [0x7C, 0x40, 0x40, 0x78, 0x40, 0x40, 0x40, 0x00]; // F
        font[71] = [0x3C, 0x44, 0x40, 0x4E, 0x44, 0x44, 0x3E, 0x00]; // G
        font[72] = [0x44, 0x44, 0x44, 0x7C, 0x44, 0x44, 0x44, 0x00]; // H
        font[73] = [0x38, 0x10, 0x10, 0x10, 0x10, 0x10, 0x38, 0x00]; // I
        font[74] = [0x04, 0x04, 0x04, 0x04, 0x04, 0x44, 0x38, 0x00]; // J
        font[75] = [0x44, 0x48, 0x50, 0x60, 0x50, 0x48, 0x44, 0x00]; // K
        font[76] = [0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x7C, 0x00]; // L
        font[77] = [0x44, 0x6C, 0x54, 0x44, 0x44, 0x44, 0x44, 0x00]; // M
        font[78] = [0x44, 0x64, 0x54, 0x4C, 0x44, 0x44, 0x44, 0x00]; // N
        font[79] = [0x38, 0x44, 0x44, 0x44, 0x44, 0x44, 0x38, 0x00]; // O
        font[80] = [0x78, 0x44, 0x44, 0x78, 0x40, 0x40, 0x40, 0x00]; // P
        font[81] = [0x38, 0x44, 0x44, 0x44, 0x54, 0x48, 0x34, 0x00]; // Q
        font[82] = [0x78, 0x44, 0x44, 0x78, 0x48, 0x44, 0x44, 0x00]; // R
        font[83] = [0x3C, 0x44, 0x40, 0x3C, 0x04, 0x44, 0x3C, 0x00]; // S
        font[84] = [0x7C, 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x00]; // T
        font[85] = [0x44, 0x44, 0x44, 0x44, 0x44, 0x44, 0x38, 0x00]; // U
        font[86] = [0x44, 0x44, 0x44, 0x44, 0x44, 0x28, 0x10, 0x00]; // V
        font[87] = [0x44, 0x44, 0x44, 0x54, 0x54, 0x6C, 0x44, 0x00]; // W
        font[88] = [0x44, 0x28, 0x10, 0x10, 0x10, 0x28, 0x44, 0x00]; // X
        font[89] = [0x44, 0x44, 0x28, 0x10, 0x10, 0x10, 0x10, 0x00]; // Y
        font[90] = [0x7C, 0x04, 0x08, 0x10, 0x20, 0x40, 0x7C, 0x00]; // Z
        // 小写字母
        font[97] = [0x00, 0x00, 0x3C, 0x04, 0x3C, 0x44, 0x3C, 0x00]; // a
        font[98] = [0x40, 0x40, 0x5C, 0x62, 0x42, 0x62, 0x5C, 0x00]; // b
        font[99] = [0x00, 0x00, 0x3C, 0x40, 0x40, 0x40, 0x3C, 0x00]; // c
        font[100] = [0x04, 0x04, 0x3C, 0x44, 0x44, 0x44, 0x3C, 0x00]; // d
        font[101] = [0x00, 0x00, 0x3C, 0x44, 0x7C, 0x40, 0x3C, 0x00]; // e
        font[102] = [0x08, 0x10, 0x38, 0x10, 0x10, 0x10, 0x08, 0x00]; // f
        font[103] = [0x00, 0x00, 0x3C, 0x44, 0x44, 0x3C, 0x04, 0x00]; // g
        font[104] = [0x40, 0x40, 0x5C, 0x62, 0x42, 0x42, 0x42, 0x00]; // h
        font[105] = [0x10, 0x00, 0x30, 0x10, 0x10, 0x10, 0x38, 0x00]; // i
        font[106] = [0x04, 0x00, 0x0C, 0x04, 0x04, 0x44, 0x38, 0x00]; // j
        font[107] = [0x40, 0x40, 0x48, 0x50, 0x60, 0x50, 0x48, 0x00]; // k
        font[108] = [0x30, 0x10, 0x10, 0x10, 0x10, 0x10, 0x38, 0x00]; // l
        font[109] = [0x00, 0x00, 0x6C, 0x54, 0x54, 0x44, 0x44, 0x00]; // m
        font[110] = [0x00, 0x00, 0x5C, 0x62, 0x42, 0x42, 0x42, 0x00]; // n
        font[111] = [0x00, 0x00, 0x3C, 0x42, 0x42, 0x42, 0x3C, 0x00]; // o
        font[112] = [0x00, 0x00, 0x5C, 0x62, 0x42, 0x5C, 0x40, 0x00]; // p
        font[113] = [0x00, 0x00, 0x3C, 0x44, 0x44, 0x3C, 0x04, 0x00]; // q
        font[114] = [0x00, 0x00, 0x5C, 0x62, 0x40, 0x40, 0x40, 0x00]; // r
        font[115] = [0x00, 0x00, 0x3C, 0x40, 0x3C, 0x04, 0x3C, 0x00]; // s
        font[116] = [0x10, 0x10, 0x38, 0x10, 0x10, 0x10, 0x08, 0x00]; // t
        font[117] = [0x00, 0x00, 0x44, 0x44, 0x44, 0x44, 0x3C, 0x00]; // u
        font[118] = [0x00, 0x00, 0x44, 0x44, 0x44, 0x28, 0x10, 0x00]; // v
        font[119] = [0x00, 0x00, 0x44, 0x44, 0x54, 0x6C, 0x44, 0x00]; // w
        font[120] = [0x00, 0x00, 0x44, 0x28, 0x10, 0x28, 0x44, 0x00]; // x
        font[121] = [0x00, 0x00, 0x44, 0x44, 0x44, 0x3C, 0x04, 0x00]; // y
        font[122] = [0x00, 0x00, 0x7C, 0x08, 0x10, 0x20, 0x7C, 0x00]; // z
        // 特殊字符
        font[32] = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]; // space
        font[45] = [0x00, 0x00, 0x00, 0x7C, 0x00, 0x00, 0x00, 0x00]; // -
        font[58] = [0x00, 0x00, 0x10, 0x00, 0x00, 0x10, 0x00, 0x00]; // :
        font[91] = [0x1C, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1C, 0x00]; // [
        font[93] = [0x38, 0x08, 0x08, 0x08, 0x08, 0x08, 0x38, 0x00]; // ]
        font
    };

    let mut cx = x;
    for ch in text.chars() {
        if cx + 8 > buf_width {
            break;
        }
        let code = ch as usize;
        if code < 128 {
            let glyph = FONT[code];
            for (row, &bits) in glyph.iter().enumerate() {
                for col in 0..8 {
                    if (bits & (0x80 >> col)) != 0 {
                        let px = cx + col;
                        let py = y + row;
                        if px < buf_width && py < buf_height {
                            buffer[py * buf_width + px] = color;
                        }
                    }
                }
            }
        }
        cx += 8;
    }
}

fn save_animation_as_gif(animation: &(Vec<Vec<u8>>, Vec<[u8; 768]>), filename: &str) -> std::io::Result<()> {
    use image::{Frame, ImageBuffer, Rgba};
    use image::codecs::gif::{GifEncoder, Repeat};
    
    let (frames, palettes) = animation;
    if frames.is_empty() {
        return Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "No frames"));
    }

    let mut gif_encoder = GifEncoder::new(File::create(filename)?);
    gif_encoder.set_repeat(Repeat::Infinite).ok();

    for (frame_data, palette) in frames.iter().zip(palettes.iter()) {
        let mut img_buffer: ImageBuffer<Rgba<u8>, Vec<u8>> = 
            ImageBuffer::new(ANI_WIDTH as u32, ANI_HEIGHT as u32);

        for (x, y, pixel) in img_buffer.enumerate_pixels_mut() {
            let idx = (y as usize) * ANI_WIDTH + (x as usize);
            let color_idx = frame_data[idx] as usize * 3;
            
            let r = (palette[color_idx] as u8).wrapping_mul(4).min(255);
            let g = (palette[color_idx + 1] as u8).wrapping_mul(4).min(255);
            let b = (palette[color_idx + 2] as u8).wrapping_mul(4).min(255);
            
            *pixel = Rgba([r, g, b, 255]);
        }

        let frame = Frame::from_parts(img_buffer, 0, 0, image::Delay::from_numer_denom_ms(100, 1));
        gif_encoder.encode_frame(frame).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
    }

    Ok(())
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

fn process_frame(param: usize, frame_data: &[u8], palette_buf: &mut [u8], pixel_buf: &mut [u8]) {
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
