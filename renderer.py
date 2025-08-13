# renderer.py
#
# Управляет контекстом ModernGL, шейдерами, буферами (VBO, VAO)
# и непосредственно процессом отрисовки сцены.
# Также отвечает за преобразование геометрии карты в 3D-меш.

import numpy as np
from wad_loader import WadLoader
import pprint

# Определим цвета
COLOR_FLOOR = (0.0, 0.5, 0.0)  # Зеленый
COLOR_CEILING = (0.8, 0.0, 0.0) # Красный
COLOR_WALL = (0.5, 0.5, 0.5)    # Серый

class MapRenderer:
    def __init__(self, map_data):
        if not map_data:
            raise ValueError("Map data cannot be None")
        self.map_data = map_data
        self.vertex_data = None

        self.vertexes = self.map_data['vertexes']
        self.linedefs = self.map_data['linedefs']
        self.sidedefs = self.map_data['sidedefs']
        self.sectors = self.map_data['sectors']

        self._build_sidedef_to_linedef_map()

    def _build_sidedef_to_linedef_map(self):
        self.sidedef_to_linedef = {}
        for i, line in enumerate(self.linedefs):
            if line.front != 0xFFFF: self.sidedef_to_linedef[line.front] = i
            if line.back != 0xFFFF: self.sidedef_to_linedef[line.back] = i

    def _trace_sector_vertices(self, sector_index):
        sector_sidedef_indices = [i for i, s in enumerate(self.sidedefs) if s.sector == sector_index]
        if not sector_sidedef_indices: return []

        edge_map = {}
        for side_idx in sector_sidedef_indices:
            linedef_idx = self.sidedef_to_linedef.get(side_idx)
            if linedef_idx is None: continue
            line = self.linedefs[linedef_idx]
            if line.front == side_idx: edge_map[line.vx_a] = (line, line.vx_b)
            else: edge_map[line.vx_b] = (line, line.vx_a)

        if not edge_map: return []
        ordered_vertices = []
        try: start_vx = next(iter(edge_map))
        except StopIteration: return []
        current_vx = start_vx
        for _ in range(len(edge_map) + 1):
            vertex_pos = self.vertexes[current_vx]
            ordered_vertices.append((vertex_pos.x, vertex_pos.y))
            _line, next_vx = edge_map.get(current_vx, (None, None))
            if next_vx is None: break
            current_vx = next_vx
            if current_vx == start_vx: break
        return ordered_vertices

    def build_level_mesh(self):
        print("Starting to build level mesh...")
        vertex_buffer_data = []

        # 1. Генерируем полы и потолки
        for i, sector in enumerate(self.sectors):
            ordered_verts_2d = self._trace_sector_vertices(i)
            if len(ordered_verts_2d) < 3: continue
            v0 = ordered_verts_2d[0]
            for j in range(1, len(ordered_verts_2d) - 1):
                v1, v2 = ordered_verts_2d[j], ordered_verts_2d[j+1]
                floor_h, ceil_h = sector.z_floor, sector.z_ceil
                # Пол
                vertex_buffer_data.extend([v0[0], floor_h, v0[1], *COLOR_FLOOR])
                vertex_buffer_data.extend([v1[0], floor_h, v1[1], *COLOR_FLOOR])
                vertex_buffer_data.extend([v2[0], floor_h, v2[1], *COLOR_FLOOR])
                # Потолок
                vertex_buffer_data.extend([v0[0], ceil_h, v0[1], *COLOR_CEILING])
                vertex_buffer_data.extend([v2[0], ceil_h, v2[1], *COLOR_CEILING])
                vertex_buffer_data.extend([v1[0], ceil_h, v1[1], *COLOR_CEILING])

        # 2. Генерируем стены
        for line in self.linedefs:
            v1_pos = self.vertexes[line.vx_a]
            v2_pos = self.vertexes[line.vx_b]

            front_sidedef = self.sidedefs[line.front]
            front_sector = self.sectors[front_sidedef.sector]

            if line.back == 0xFFFF: # Односторонняя стена
                fh, ch = front_sector.z_floor, front_sector.z_ceil
                p1 = (v1_pos.x, fh, v1_pos.y)
                p2 = (v2_pos.x, fh, v2_pos.y)
                p3 = (v2_pos.x, ch, v2_pos.y)
                p4 = (v1_pos.x, ch, v1_pos.y)
                vertex_buffer_data.extend([*p1, *COLOR_WALL, *p2, *COLOR_WALL, *p3, *COLOR_WALL])
                vertex_buffer_data.extend([*p1, *COLOR_WALL, *p3, *COLOR_WALL, *p4, *COLOR_WALL])
            else: # Двусторонняя стена, возможны "порталы"
                back_sidedef = self.sidedefs[line.back]
                back_sector = self.sectors[back_sidedef.sector]

                # Верхняя стена (ступенька потолка)
                if front_sector.z_ceil > back_sector.z_ceil:
                    fh, ch = back_sector.z_ceil, front_sector.z_ceil
                    p1 = (v1_pos.x, fh, v1_pos.y); p2 = (v2_pos.x, fh, v2_pos.y)
                    p3 = (v2_pos.x, ch, v2_pos.y); p4 = (v1_pos.x, ch, v1_pos.y)
                    vertex_buffer_data.extend([*p1, *COLOR_WALL, *p2, *COLOR_WALL, *p3, *COLOR_WALL])
                    vertex_buffer_data.extend([*p1, *COLOR_WALL, *p3, *COLOR_WALL, *p4, *COLOR_WALL])

                # Нижняя стена (ступенька пола)
                if front_sector.z_floor < back_sector.z_floor:
                    fh, ch = front_sector.z_floor, back_sector.z_floor
                    p1 = (v1_pos.x, fh, v1_pos.y); p2 = (v2_pos.x, fh, v2_pos.y)
                    p3 = (v2_pos.x, ch, v2_pos.y); p4 = (v1_pos.x, ch, v1_pos.y)
                    vertex_buffer_data.extend([*p1, *COLOR_WALL, *p2, *COLOR_WALL, *p3, *COLOR_WALL])
                    vertex_buffer_data.extend([*p1, *COLOR_WALL, *p3, *COLOR_WALL, *p4, *COLOR_WALL])

        if not vertex_buffer_data:
            print("Warning: No vertices were generated for the mesh.")
            return False

        self.vertex_data = np.array(vertex_buffer_data, dtype='f4')
        print(f"Mesh built successfully. Total vertices: {len(self.vertex_data) // 6}")
        return True

# Пример использования:
if __name__ == '__main__':
    print("--- Testing Renderer ---")
    wad_loader = WadLoader('test.wad')
    map_name = wad_loader.get_map_names()[0]
    map_data = wad_loader.read_map_data(map_name)
    if map_data:
        map_renderer = MapRenderer(map_data)
        success = map_renderer.build_level_mesh()
        if success:
            print("\nRenderer test completed successfully.")
            print(f"Generated Vertex Buffer Shape: {map_renderer.vertex_data.shape}")
            print(f"Vertex Buffer Size (bytes): {map_renderer.vertex_data.nbytes}")
        else:
            print("\nRenderer test failed.")
    else:
        print("Could not load map data to test renderer.")
