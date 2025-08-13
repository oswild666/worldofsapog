# main.py
#
# Главный файл приложения. Инициализирует рендерер,
# создает сцену в headless-режиме и сохраняет результат в файл.

import moderngl
import numpy as np
from PIL import Image

from wad_loader import WadLoader
from renderer import MapRenderer

def main():
    print("Engine starting in headless mode...")

    # --- Размеры изображения ---
    width, height = 1280, 720

    # --- Загрузка и обработка геометрии ---
    print("Loading map data...")
    wad_loader = WadLoader('test.wad')
    map_name = wad_loader.get_map_names()[0]
    map_data = wad_loader.read_map_data(map_name)
    if not map_data:
        raise RuntimeError("Failed to load map data.")

    print("Building level mesh...")
    map_renderer = MapRenderer(map_data)
    map_renderer.build_level_mesh()
    if map_renderer.vertex_data is None:
        raise RuntimeError("Failed to build level mesh.")

    # --- Настройка ModernGL в headless-режиме ---
    try:
        ctx = moderngl.create_standalone_context(require=330)
        print("ModernGL standalone context created.")
    except Exception as e:
        print(f"Could not create standalone context: {e}")
        print("This might be due to missing graphics drivers or running in an environment without any GL capabilities.")
        return

    prog = ctx.program(
        vertex_shader='''
            #version 330
            uniform mat4 mvp;
            in vec3 in_vert;
            in vec3 in_color;
            out vec3 v_color;
            void main() {
                gl_Position = mvp * vec4(in_vert, 1.0);
                v_color = in_color;
            }
        ''',
        fragment_shader='''
            #version 330
            in vec3 v_color;
            out vec4 f_color;
            void main() {
                f_color = vec4(v_color, 1.0);
            }
        '''
    )
    mvp = prog['mvp']
    vbo = ctx.buffer(map_renderer.vertex_data)
    vao = ctx.vertex_array(prog, [(vbo, '3f 3f', 'in_vert', 'in_color')])

    # --- Создание Framebuffer для рендеринга в текстуру ---
    color_rbo = ctx.renderbuffer((width, height))
    depth_rbo = ctx.depth_renderbuffer((width, height))
    fbo = ctx.framebuffer(color_attachments=[color_rbo], depth_attachment=depth_rbo)

    # --- Рендеринг сцены ---
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0) # Черный фон
    ctx.enable(moderngl.DEPTH_TEST)

    # Временная камера (смотрим сверху, немного под углом)
    # Матрица проекции
    proj = np.array([
        [1.7, 0.0, 0.0, 0.0],
        [0.0, 2.4, 0.0, 0.0],
        [0.0, 0.0, -1.0, -0.2],
        [0.0, 0.0, -1.0, 0.0]
    ]).astype('f4').T

    # Матрица вида
    look_at = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.8, 0.5, -4000.0],
        [0.0, -0.5, 0.8, -4000.0],
        [0.0, 0.0, 0.0, 1.0]
    ]).astype('f4').T

    scale = np.identity(4, dtype='f4')
    scale[0, 0] = scale[1, 1] = scale[2, 2] = 0.0001

    mvp_matrix = proj @ look_at @ scale
    mvp.write(mvp_matrix)

    vao.render()
    print("Scene rendered to framebuffer.")

    # --- Сохранение результата в файл ---
    image = Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1)
    output_filename = 'output.png'
    image.save(output_filename)
    print(f"Render saved to '{output_filename}'")

    # --- Очистка ресурсов ---
    vao.release()
    vbo.release()
    prog.release()
    fbo.release()
    ctx.release()
    print("Resources released. Engine stopped.")

if __name__ == "__main__":
    main()
