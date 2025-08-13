# wad_loader.py
#
# Отвечает за загрузку и парсинг WAD-файлов с использованием omgifol.
# Извлекает геометрию уровня, данные о вещах (things) и т.д.

import omg
import pprint

class WadLoader:
    def __init__(self, wad_path):
        """
        Инициализирует загрузчик и открывает WAD-файл.
        :param wad_path: Путь к WAD-файлу.
        """
        try:
            self.wad = omg.WAD(wad_path)
        except FileNotFoundError:
            print(f"Error: WAD file not found at '{wad_path}'")
            self.wad = None
        except Exception as e:
            print(f"An error occurred while loading WAD file: {e}")
            self.wad = None

    def get_map_names(self):
        if not self.wad:
            return []
        return list(self.wad.maps.keys())

    def read_map_data(self, map_name):
        """
        Извлекает все необходимые данные из указанной карты.
        :param map_name: Имя карты (например, 'MAP01' или 'E1M1').
        :return: Словарь с данными карты или None, если карта не найдена.
        """
        if not self.wad or map_name not in self.wad.maps:
            print(f"Error: Map '{map_name}' not found in WAD file.")
            return None

        map_editor = omg.MapEditor(self.wad.maps[map_name])

        player_start = None
        for thing in map_editor.things:
            # Тип 1 - это старт Игрока 1 в одиночной игре
            if thing.type == 1:
                player_start = {
                    'x': thing.x,
                    'y': thing.y,
                    'angle': thing.angle
                }
                break

        if not player_start:
            print(f"Warning: Player 1 start not found in map '{map_name}'.")

        map_data = {
            'name': map_name,
            'vertexes': map_editor.vertexes,
            'linedefs': map_editor.linedefs,
            'sidedefs': map_editor.sidedefs,
            'sectors': map_editor.sectors,
            'things': map_editor.things,
            'player_start': player_start
        }
        return map_data

# Пример использования
if __name__ == '__main__':
    wad_loader = WadLoader('test.wad')

    if wad_loader.wad:
        map_names = wad_loader.get_map_names()
        if not map_names:
            print("No maps found in the WAD file.")
        else:
            map_name_to_load = map_names[0]
            print(f"Reading data from map: '{map_name_to_load}'")

            map_data = wad_loader.read_map_data(map_name_to_load)

            if map_data:
                print("\nSuccessfully extracted map data:")
                print(f" - Vertices: {len(map_data['vertexes'])}")
                print(f" - Linedefs: {len(map_data['linedefs'])}")
                print(f" - Sidedefs: {len(map_data['sidedefs'])}")
                print(f" - Sectors: {len(map_data['sectors'])}")
                print(f" - Things: {len(map_data['things'])}")

                if map_data['player_start']:
                    print("\nPlayer 1 Start Position found:")
                    pprint.pprint(map_data['player_start'])
                else:
                    print("\nPlayer 1 Start Position not found.")
