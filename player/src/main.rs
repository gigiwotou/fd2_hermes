use minifb::{Key, Window, WindowOptions};
use std::fs::File;
use std::io::Read;

const SCREEN_WIDTH: usize = 320;
const SCREEN_HEIGHT: usize = 200;
const BUFFER_SIZE: usize = SCREEN_WIDTH * SCREEN_HEIGHT;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let ani_path = if args.len() > 1 {
        &args[1]
    } else {
        "../game/ANI.DAT"
    };

    // 读取 ANI.DAT
    let mut file = match File::open(ani_path) {
        Ok(f) => f,
        Err(_) => {
            eprintln!("无法打开文件: {}", ani_path);
            return;
        }
    };

    let mut data = Vec::new();
    file.read_to_end(&mut data).unwrap();

    // 解析 AFM 索引
    let afm_offsets = parse_afm_index(&data);
    println!("找到 {} 个 AFM 动画", afm_offsets.len());
    println!("控制:");
    println!("  数字键 1-9: 选择动画");
    println!("  左/右方向键: 切换动画");
    println!("  ESC: 退出");

    // 解码所有 AFM
    let mut all_animations: Vec<(Vec<Vec<u8>>, Vec<[u8; 768]>)> = Vec::new();
    
    for (idx, &offset) in afm_offsets.iter().enumerate() {
        let (frames, palettes) = decode_afm(&data, offset);
        println!("AFM {}: {} 帧", idx, frames.len());
        all_animations.push((frames, palettes));
    }

    if all_animations.is_empty() {
        eprintln!("没有找到动画");
        return;
    }

    // 创建窗口
    let mut window = Window::new(
        "FD2 Animation Player",
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        WindowOptions {
            scale: minifb::Scale::X2,
            ..WindowOptions::default()
        },
    )
    .unwrap();

    let mut current_afm = 0;
    let mut current_frame = 0;
    let mut frame_counter = 0;
    let mut buffer = vec![0u32; BUFFER_SIZE];

    // 数字键映射
    let num_keys = [
        Key::Key1, Key::Key2, Key::Key3, Key::Key4, Key::Key5,
        Key::Key6, Key::Key7, Key::Key8, Key::Key9,
    ];

    while window.is_open() && !window.is_key_down(Key::Escape) {
        // 按键选择动画
        for (i, &key) in num_keys.iter().enumerate() {
            if window.is_key_pressed(key, minifb::KeyRepeat::No) {
                if i < all_animations.len() {
                    current_afm = i;
                    current_frame = 0;
                    println!("切换到 AFM {}", current_afm);
                }
            }
        }

        // 左右键切换动画
        if window.is_key_pressed(Key::Left, minifb::KeyRepeat::No) {
            if current_afm > 0 {
                current_afm -= 1;
                current_frame = 0;
                println!("切换到 AFM {}", current_afm);
            }
        }
        if window.is_key_pressed(Key::Right, minifb::KeyRepeat::No) {
            if current_afm < all_animations.len() - 1 {
                current_afm += 1;
                current_frame = 0;
                println!("切换到 AFM {}", current_afm);
            }
        }

        // 播放动画
        let (frames, palettes) = &all_animations[current_afm];
        if !frames.is_empty() {
            // 更新帧
            frame_counter += 1;
            if frame_counter >= 3 {
                // 约 10 FPS (30 / 3)
                frame_counter = 0;
                current_frame = (current_frame + 1) % frames.len();
            }

            // 更新窗口标题
            let title = format!(
                "FD2 Player - AFM {} ({}/{})",
                current_afm,
                current_frame + 1,
                frames.len()
            );
            window.set_title(&title);

            // 绘制帧
            let frame_data = &frames[current_frame];
            let palette = &palettes[current_frame];
            convert_to_rgba(frame_data, palette, &mut buffer);
            window.update_with_buffer(&buffer, SCREEN_WIDTH, SCREEN_HEIGHT).unwrap();
        } else {
            window.update();
        }

        std::thread::sleep(std::time::Duration::from_millis(33)); // ~30 FPS
    }
}

fn parse_afm_index(data: &[u8]) -> Vec<usize> {
    let mut offsets = Vec::new();
    let mut pos = 6;

    while pos + 4 <= data.len() {
        let offset = u32::from_le_bytes([data[pos], data[pos + 1], data[pos + 2], data[pos + 3]]) as usize;
        if offset == 0 {
            break;
        }

        // 检查是否是有效的 AFM
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

        // 只保存有变化的帧
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
                // 填充调色板
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
                // 复制调色板
                if data_pos + 768 <= frame_data.len() {
                    palette_buf.copy_from_slice(&frame_data[data_pos..data_pos + 768]);
                    data_pos += 768;
                }
            }
            0x02 => {
                // RLE 解码调色板
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
                // 填充像素缓冲区
                if data_pos < frame_data.len() {
                    let fill_byte = frame_data[data_pos];
                    data_pos += 1;
                    for i in 0..BUFFER_SIZE {
                        pixel_buf[i] = fill_byte;
                    }
                }
            }
            0x05 => {
                // 复制像素数据
                if data_pos + BUFFER_SIZE <= frame_data.len() {
                    pixel_buf.copy_from_slice(&frame_data[data_pos..data_pos + BUFFER_SIZE]);
                    data_pos += BUFFER_SIZE;
                }
            }
            0x06 => {
                // RLE 解码像素
                let (consumed, _) = decode_rle(&frame_data[data_pos..], pixel_buf);
                data_pos += consumed;
            }
            0x07 => {
                // 点绘制
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
                // 填充段
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
                // 复制数据
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

fn convert_to_rgba(frame_data: &[u8], palette: &[u8; 768], buffer: &mut [u32]) {
    for (i, &pixel) in frame_data.iter().enumerate() {
        let idx = pixel as usize * 3;
        let r = (palette[idx] as u32 * 4).min(255);
        let g = (palette[idx + 1] as u32 * 4).min(255);
        let b = (palette[idx + 2] as u32 * 4).min(255);
        buffer[i] = (r << 16) | (g << 8) | b;
    }
}
