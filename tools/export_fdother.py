#!/usr/bin/env python3
"""
使用FD2ResViewer的解析逻辑导出FDOTHER.DAT中的所有图片
"""
import os
import sys
import struct
from PIL import Image

# 添加parsers目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.base_parser import DataBlock, ColorPanel, BMPMaker

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
OUTPUT_DIR = '/home/yinming/fd2_hermes/decoded_images_fd2resviewer'

class FDOtherExporter:
    def __init__(self):
        self.fileDatas = None
        self.datablocksOTHER = [None] * 104
        self.datablocksOTHERSubs = None
        self.bmp_maker = BMPMaker()
        
    def load_file(self, path):
        with open(path, 'rb') as f:
            self.fileDatas = f.read()
        print(f"加载文件: {len(self.fileDatas)} 字节")
        
    def analysis(self):
        """分析FDOTHER数据结构"""
        array = [0] * 104
        num = 6
        while num <= 418:  # 6 + (104-1)*4 = 418
            index = int((num - 6) / 4)
            if num + 4 <= len(self.fileDatas):
                array[index] = struct.unpack('<I', self.fileDatas[num:num+4])[0]
            num += 4

        num4 = len(array) - 2
        num5 = 0
        while num5 <= num4:
            if num5 < len(self.datablocksOTHER) and num5 + 1 < len(array):
                self.datablocksOTHER[num5] = DataBlock(array[num5], array[num5 + 1] - array[num5])
            num5 += 1
        if num5 < len(self.datablocksOTHER) and num5 < len(array) and self.fileDatas is not None:
            self.datablocksOTHER[num5] = DataBlock(array[num5], len(self.fileDatas) - array[num5])

        # 处理子索引
        for sub_index in range(104):
            self.analysis_subs(sub_index)
            
        return self.datablocksOTHER

    def analysis_subs(self, subIndex):
        """分析FDOTHER子数据结构"""
        if subIndex in (1, 14):
            if self.datablocksOTHER[subIndex] is None or self.fileDatas is None:
                return
            datablock = self.datablocksOTHER[subIndex]
            if datablock is None:
                return
            num43 = datablock.startOffset + 6
            sWidth = struct.unpack('<h', self.fileDatas[datablock.startOffset:datablock.startOffset+2])[0]
            sHeight = struct.unpack('<h', self.fileDatas[datablock.startOffset+2:datablock.startOffset+4])[0]
            num44 = struct.unpack('<h', self.fileDatas[datablock.startOffset+4:datablock.startOffset+6])[0]
            self.datablocksOTHERSubs = [None] * num44
            array5 = [0] * num44
            num45 = num44 - 1
            num46 = 0
            while num46 <= num45:
                array5[num46] = struct.unpack('<I', self.fileDatas[num43 + num46*4:num43 + (num46+1)*4])[0]
                num46 += 1

            num48 = num44 - 2
            num46 = 0
            while num46 <= num48:
                if self.datablocksOTHERSubs is not None:
                    self.datablocksOTHERSubs[num46] = DataBlock(array5[num46], array5[num46+1] - array5[num46])
                num46 += 1
            if self.datablocksOTHERSubs is not None:
                self.datablocksOTHERSubs[num46] = DataBlock(array5[num46], datablock.length - array5[num46])

        elif subIndex == 2:
            if self.datablocksOTHER[subIndex] is None or self.fileDatas is None:
                return
            datablock = self.datablocksOTHER[subIndex]
            if datablock is None:
                return
            startOffset2 = datablock.startOffset
            num34 = int(struct.unpack('<I', self.fileDatas[startOffset2:startOffset2+4])[0] / 4)
            array4 = [0] * num34
            self.datablocksOTHERSubs = [None] * num34
            num36 = 0
            while num36 < num34:
                array4[num36] = struct.unpack('<I', self.fileDatas[startOffset2 + num36*4:startOffset2 + (num36+1)*4])[0]
                num36 += 1

            num38 = num34 - 2
            num36 = 0
            while num36 <= num38:
                if self.datablocksOTHERSubs is not None:
                    self.datablocksOTHERSubs[num36] = DataBlock(array4[num36], array4[num36+1] - array4[num36])
                num36 += 1
            if self.datablocksOTHERSubs is not None:
                self.datablocksOTHERSubs[num36] = DataBlock(array4[num36], datablock.length - array4[num36])

        elif subIndex == 4:
            if self.datablocksOTHER[subIndex] is None:
                return
            datablock = self.datablocksOTHER[subIndex]
            if datablock is None:
                return
            obj = datablock.length / 32
            array2 = [i*32 for i in range(int(obj))]
            self.datablocksOTHERSubs = [None] * len(array2)
            num17 = 0
            while num17 < len(array2)-1:
                if self.datablocksOTHERSubs is not None:
                    self.datablocksOTHERSubs[num17] = DataBlock(array2[num17], array2[num17+1] - array2[num17])
                num17 += 1
            if self.datablocksOTHERSubs is not None:
                self.datablocksOTHERSubs[num17] = DataBlock(array2[num17], datablock.length - array2[num17])

        elif subIndex in (5, 6, 9, 96):
            if self.datablocksOTHER[subIndex] is None or self.fileDatas is None:
                return
            datablock = self.datablocksOTHER[subIndex]
            if datablock is None:
                return
            num3 = datablock.startOffset + 4
            num4 = struct.unpack('<h', self.fileDatas[num3:num3+2])[0]
            array = [0] * num4
            self.datablocksOTHERSubs = [None] * num4
            num6 = 0
            while num6 < num4:
                array[num6] = struct.unpack('<I', self.fileDatas[num3+2 + num6*4:num3+6 + num6*4])[0]
                num6 += 1

            num9 = num4 - 2
            num6 = 0
            while num6 <= num9:
                if self.datablocksOTHERSubs is not None:
                    self.datablocksOTHERSubs[num6] = DataBlock(array[num6], array[num6+1] - array[num6])
                num6 += 1
            if self.datablocksOTHERSubs is not None:
                self.datablocksOTHERSubs[num6] = DataBlock(array[num6], datablock.length - array[num6])

        elif subIndex in (7, 12, 13, 63):
            if self.datablocksOTHER[subIndex] is None or self.fileDatas is None:
                return
            datablock = self.datablocksOTHER[subIndex]
            if datablock is None:
                return
            num24 = datablock.startOffset + 6
            short_value = struct.unpack('<h', self.fileDatas[num24:num24+2])[0]
            num25 = int(round((short_value - 6) / 4.0 - 1.0))
            num25 = max(0, num25)
            array3 = [0] * num25
            self.datablocksOTHERSubs = [None] * num25
            num26 = num25 - 1
            num27 = 0
            while num27 <= num26:
                array3[num27] = struct.unpack('<I', self.fileDatas[num24 + num27*4:num24 + (num27+1)*4])[0]
                num27 += 1

            num29 = len(array3) - 2
            num27 = 0
            while num27 <= num29:
                if self.datablocksOTHERSubs is not None:
                    self.datablocksOTHERSubs[num27] = DataBlock(array3[num27], array3[num27+1] - array3[num27])
                num27 += 1
            if self.datablocksOTHERSubs is not None:
                self.datablocksOTHERSubs[num27] = DataBlock(array3[num27], datablock.length - array3[num27])

    def export_images(self, output_dir):
        """导出所有图片"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 处理不同类型的资源
        for subIndex in range(104):
            if self.datablocksOTHER[subIndex] is None:
                continue
                
            datablock = self.datablocksOTHER[subIndex]
            
            # 子索引资源
            self.analysis_subs(subIndex)
            
            if self.datablocksOTHERSubs and len(self.datablocksOTHERSubs) > 0:
                for num2, dbSub in enumerate(self.datablocksOTHERSubs):
                    if dbSub is None:
                        continue
                    start_offset = datablock.startOffset + dbSub.startOffset
                    self._export_single_image(subIndex, num2, start_offset, dbSub.length, output_dir)
            else:
                # 直接导出的资源
                self._export_single_image(subIndex, 0, datablock.startOffset, datablock.length, output_dir)
                
    def _export_single_image(self, subIndex, num2, start_offset, length, output_dir):
        """导出单张图片"""
        try:
            if start_offset + 4 > len(self.fileDatas):
                return
                
            sWidth = struct.unpack('<h', self.fileDatas[start_offset:start_offset+2])[0]
            sHeight = struct.unpack('<h', self.fileDatas[start_offset+2:start_offset+4])[0]
            
            if sWidth <= 0 or sHeight <= 0 or sWidth > 500 or sHeight > 500:
                return
                
            colorpanel = ColorPanel(1)
            
            # 根据subIndex选择正确的解码方法
            if subIndex in (10, 15):
                image = self.bmp_maker.makeFaceBMP(self.fileDatas, start_offset, length, colorpanel)
                filename = f'face_{subIndex}_{num2:03d}.png'
            elif subIndex in (11, 16, 17, 46, 47, 56, 59, 60, 61, 62, 69, 70, 71, 72, 73, 74, 75, 97, 98, 100):
                image = self.bmp_maker.makeShapBMP(sWidth, sHeight, self.fileDatas, start_offset + 4, length - 4, colorpanel)
                filename = f'shap_{subIndex}_{num2:03d}.png'
            elif subIndex == 55:
                image = self.bmp_maker.makeBMP(sWidth, sHeight, self.fileDatas, start_offset + 4, length - 4, colorpanel)
                filename = f'other_{subIndex}_{num2:03d}.png'
            elif subIndex == 4:
                image = self.bmp_maker.makeFontBMP(self.fileDatas, start_offset, length)
                filename = f'font_{subIndex}_{num2:03d}.png'
            else:
                # 默认使用makeBMP
                image = self.bmp_maker.makeBMP(sWidth, sHeight, self.fileDatas, start_offset + 4, length - 4, colorpanel)
                filename = f'img_{subIndex}_{num2:03d}.png'
            
            if image:
                filepath = os.path.join(output_dir, filename)
                image.save(filepath)
                print(f"导出: {filename}")
                
        except Exception as e:
            print(f"导出失败 subIndex={subIndex}, num2={num2}: {e}")

def main():
    exporter = FDOtherExporter()
    exporter.load_file(DAT_FILE)
    exporter.analysis()
    exporter.export_images(OUTPUT_DIR)
    print(f"\n导出完成: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()