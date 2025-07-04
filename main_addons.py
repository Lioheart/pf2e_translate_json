import json
import os
import pathlib
import shutil
import zipfile
from pprint import pprint

import plyvel
from urllib.request import urlretrieve

import requests

# sudo apt-get install libleveldb-dev

LORE_NAMES = [
    'Acrobatics',
    'Arcana',
    'Athletics',
    'Crafting',
    'Deception',
    'Diplomacy',
    'Intimidation',
    'Medicine',
    'Nature',
    'Occultism',
    'Performance',
    'Religion',
    'Society',
    'Stealth',
    'Survival',
    'Thievery'
]


def remove_folders_except_venv():
    source_dir = "."  # Domyślna lokalizacja (bieżący katalog)

    # Przeglądaj foldery w katalogu źródłowym
    for folder_name in os.listdir(source_dir):
        folder_path = os.path.join(source_dir, folder_name)

        # Sprawdź, czy to folder i nie jest to folder "venv"
        if os.path.isdir(folder_path) and folder_name != "venv":
            # Usuń folder wraz z zawartością
            shutil.rmtree(folder_path)


def clean():
    folder_path = os.getcwd()
    # Przejdź przez wszystkie pliki w folderze
    for file_name_clean in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name_clean)

        # Sprawdź, czy plik ma rozszerzenie .json lub .zip i usuń go
        if file_name_clean.endswith('.json') or file_name_clean.endswith('.zip'):
            os.remove(file_path)
            print(f'Usunięto: {file_name_clean}')


def copy_addon_folders():
    source_dir = "."
    target_dir = "all_addons"

    # Upewnij się, że folder docelowy istnieje
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Przeglądaj foldery w katalogu źródłowym
    for folder_name in os.listdir(source_dir):
        folder_path = os.path.join(source_dir, folder_name)

        # Sprawdź, czy to folder i czy jego nazwa zaczyna się na "addon"
        if os.path.isdir(folder_path) and folder_name.startswith("addon"):
            # Skopiuj zawartość folderu do katalogu docelowego bez tworzenia nowego folderu
            for item in os.listdir(folder_path):
                s = os.path.join(folder_path, item)
                d = os.path.join(target_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)


def read_leveldb_to_json(leveldb_path, output_json_path):
    print(leveldb_path)
    print(output_json_path)
    def list_subfolders(directory):
        try:
            # Lista folderów w katalogu
            subfolders = [f.name for f in os.scandir(directory) if f.is_dir()]

            # Zwróć nazwy folderów, jeśli istnieją
            if subfolders:
                return subfolders
            else:
                return "Brak folderów w katalogu"
        except Exception as error:
            raise f"Wystąpił błąd list_subfolders: {error}"

    folders_list = list_subfolders(leveldb_path.replace('\\', '/'))
    for sub_folders in folders_list:
        output_path = rf'{output_json_path}\{sub_folders}.json'
        output_folder = rf'{output_json_path.split("\\")[0]}\packs\{sub_folders}'.replace('\\', '/')
        if output_json_path.split("\\")[1] == 'pf2e-macros':
            output_folder = rf'{output_json_path.split("\\")[0]}\pf2e-macros\packs\{sub_folders}'.replace('\\', '/')
        print('output_folder', output_folder)

        # Ensure the output folder exists
        output_file = output_path.replace('\\', '/')
        output_dir = output_json_path.replace('\\', '/')
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Otwórz bazę danych LevelDB
            db = plyvel.DB(output_folder, create_if_missing=False)

            # Stwórz pustą listę na dane
            data = []

            # Iteruj przez wszystkie klucze i wartości w bazie danych
            for key, value in db:
                try:
                    value_str = value.decode('utf-8', errors='ignore')
                    # Jeśli wartość to poprawny JSON, konwertujemy ją do obiektu
                    try:
                        value_data = json.loads(value_str)
                    except json.JSONDecodeError:
                        value_data = {"name": value_str}  # Jeśli to nie JSON, utwórz obiekt z kluczem "name"

                    # Dodaj tylko wartość do listy
                    data.append(value_data)
                except Exception as e:
                    print(f"Błąd dekodowania dla klucza {key}: {e}")
                    continue

            # Zapisz dane do pliku JSON jako listę
            with open(output_file, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)

            print(f"Dane zostały zapisane do {output_file}")
        except Exception as e:
            raise f"Wystąpił błąd read_leveldb_to_json: {e}"
        finally:
            db.close()


def exclude_empty_prerequisites(input_dict):
    if isinstance(input_dict, dict):
        result_dict = input_dict.copy()

        for key, value in input_dict.items():
            if key == "prerequisites" and isinstance(value, dict) and value.get("value") == []:
                result_dict.pop(key, None)
            elif isinstance(value, (dict, list)):
                result_dict[key] = exclude_empty_prerequisites(value)

        return result_dict
    elif isinstance(input_dict, list):
        return [exclude_empty_prerequisites(item) for item in input_dict]
    else:
        return input_dict


def sort_entries(input_dict):
    if "entries" in input_dict:
        input_dict["entries"] = dict(sorted(input_dict["entries"].items()))

    for key, value in input_dict.items():
        if isinstance(value, dict):
            input_dict[key] = sort_entries(value)

    return input_dict


def move_files(source_folder_bad, destination_folder):
    # Sprawdź, czy folder źródłowy istnieje
    if not os.path.exists(source_folder_bad):
        print("Folder źródłowy nie istnieje.")
        return

    # Stwórz folder docelowy, jeśli nie istnieje
    os.makedirs(destination_folder, exist_ok=True)

    # Przenieś pliki z folderu źródłowego do docelowego
    for filename in os.listdir(source_folder_bad):
        src_file = os.path.join(source_folder_bad, filename)
        dest_file = os.path.join(destination_folder, filename)
        shutil.move(src_file, dest_file)
        print(f"Przeniesiono: {filename}")

    print("Przenoszenie zakończone.")


def remove_empty_values(input_dict):
    if isinstance(input_dict, dict):
        # Kopiowanie słownika, aby nie modyfikować oryginalnego
        result_dict = input_dict.copy()

        # Rekurencyjne usuwanie pustych wartości
        for key, value in input_dict.items():
            if value is None or (isinstance(value, (dict, list)) and not value):
                result_dict.pop(key, None)
            elif isinstance(value, dict):
                result_dict[key] = remove_empty_values(value)
            elif isinstance(value, list):
                result_dict[key] = [remove_empty_values(item) for item in value]

        return result_dict
    elif isinstance(input_dict, list):
        # Rekurencyjne usuwanie pustych wartości z listy
        return [remove_empty_values(item) for item in input_dict]
    else:
        # Zwróć niezmienioną wartość, jeśli nie jest to ani słownik, ani lista
        return input_dict


def download_and_extract_zip(zip_url, zip_filename, extract_folder_zip):
    response = requests.get(zip_url)

    with open(zip_filename, 'wb') as zip_file:
        zip_file.write(response.content)

    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder_zip)


def convert_extension(file_path, old_extension, new_extension):
    old_file = os.path.join(file_path, f"{old_extension}.db").replace("\\", "/")
    new_file = os.path.join(file_path, f"{new_extension}.json").replace("\\", "/")

    # Wczytaj zawartość z pliku
    with open(old_file, 'r') as file:
        data = file.read()
    # Zamień znaki nowej linii między obiektami na przecinki
    data = data.strip().replace('\n', ',\n')

    # Dodaj kwadratowe nawiasy, aby uzyskać poprawny format listy obiektów JSON
    json_data = f'[{data}]'

    # Wczytaj dane JSON
    parsed_data = json.loads(json_data)

    # Zapisz dane do pliku JSON
    with open(new_file, 'w', encoding='utf-8') as outfile:
        json.dump(parsed_data, outfile, ensure_ascii=False, indent=4)

    os.remove(old_file)


def create_version_directory(version):
    if os.path.exists(version):
        print(f'Katalog {version} istnieje, pomijam tworzenie.')
        return False
    else:
        print(f'Tworzę katalog {version}')
        os.makedirs(version)
        return True


def process_files(folders, version, type_system):
    dict_key = []
    for root, dirs, files in os.walk(folders):
        for file in files:
            if file == "relic-macros.json":
                continue
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                print('Oryginalny plik:', file)
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)

                try:
                    compendium = data[0]
                except (KeyError, AttributeError) as e:
                    compendium = data

                keys = compendium.keys()
                print('Klucze pliku JSON:', list(keys))
                if '_id' not in keys and type_system == 'system':
                    print('Inny plik, pomiń')
                    shutil.copy(file_path, version)
                    continue

                try:
                    name = compendium['_stats']['compendiumSource'].split('.')
                    new_name = fr'{version}/{name[1]}.{name[2]}.json'
                except KeyError:
                    new_name = fr'{version}/pf2e.{file}'
                except AttributeError:
                    new_name = fr'{version}/starfinder-field-test-for-pf2e.{file}'
                except IndexError:
                    if type_system == 'pf2e-animal-companions':
                        name = [None, type_system, 'AC-Advanced-Maneuvers']
                        new_name = fr'{version}/{name[1]}.{name[2]}.json'
                if type_system.startswith('pf2e'):
                    new_name = fr'{version}/{type_system}.{file}'
                elif type_system.startswith('star'):
                    new_name = fr'{version}/starfinder-field-test-for-pf2e.{file}'
                print('Nowy plik:', new_name)
                print()

                if file in ('kingmaker-tools-rolltables.json', 'kingmaker-tools-random-encounters.json', 'kingmaker-tools-settlements.json'):
                    continue

                if pathlib.Path(f'{root}/{file.split(".")[0]}_folders.json').is_file():
                    transifex_dict = {
                        "label": file.split('.')[0].title(),
                        "folders": {},
                        "entries": {},
                        "mapping": {}
                    }

                    with open(f'{root}/{file.split(".")[0]}_folders.json', 'r', encoding='utf-8') as json_file:
                        data_folder = json.load(json_file)

                    for new_data in data_folder:
                        name = new_data["name"].strip()
                        transifex_dict["folders"].update({name: name})

                elif 'color' in keys or 'folder' in keys:
                    transifex_dict = {
                        "label": file.split('.')[0].title(),
                        "folders": {},
                        "entries": {},
                        "mapping": {}
                    }
                else:
                    transifex_dict = {
                        "label": file.split('.')[0].title(),
                        "entries": {},
                        "mapping": {}
                    }
                if file == 'spells.json':
                    transifex_dict["mapping"].update(
                        {
                            "areadetails": "system.area.details",
                            "cost": "system.cost.value",
                            "duration": "system.duration.value",
                            "range": "system.range.value",
                            "requirements": "system.requirements",
                            "target": "system.target.value",
                            "time": "system.time.value",
                            "primarycheck": "system.ritual.primary.check",
                            "secondarycheck": "system.ritual.secondary.checks",
                            "gmNote": "system.description.gm",
                            "heightening": {
                                "converter": "translateHeightening",
                                "path": "system.heightening.levels"
                            },
                            "spellVariants": {
                                "converter": "translateSpellVariant",
                                "path": "system.overlays"
                            }
                        }
                    )

                flag = []
                for new_data in data:
                    name = new_data["name"].strip()
                    # Dla folderów
                    if 'folder' in new_data.keys() and 'color' in new_data.keys():
                        transifex_dict["folders"].update({name: name})
                        continue

                    # Dla Kompendium bez opisu
                    elif 'items' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})

                    # Dla Makr
                    elif 'command' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})

                    # Dla Dzienników
                    elif 'journal' in keys:
                        transifex_dict["entries"][name.strip()].update({"journals": {}})
                        for journal in new_data["journal"]:
                            transifex_dict["entries"][name]["journals"].update({journal["name"]: {}})
                            transifex_dict["entries"][name]["journals"][journal["name"].strip()].update(
                                {"name": journal["name"]})
                            transifex_dict["entries"][name]["journals"][journal["name"]].update({"pages": {}})
                            for pages in journal["pages"]:
                                transifex_dict["entries"][name]["journals"][journal["name"]]["pages"].update(
                                    {pages["name"].strip(): {}})
                                transifex_dict["entries"][name]["journals"][journal["name"]]["pages"][
                                    pages["name"].strip()].update({"name": pages["name"].strip()})
                                transifex_dict["entries"][name]["journals"][journal["name"]]["pages"][
                                    pages["name"].strip()].update(
                                    {"text": " ".join(pages["text"].get("content", "").split())})

                    elif 'permission' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        transifex_dict["entries"][name].update({"pages": {}})
                        transifex_dict["entries"][name]['pages'].update({name: {}})
                        transifex_dict["entries"][name]['pages'][name].update({"name": name})
                        try:  # Warunek dla exploration-effects!!!
                            # TODO: Dodać to do tłumaczenia!
                            transifex_dict["entries"][name]['pages'][name].update({"text": new_data['content']})
                        except KeyError:
                            del transifex_dict["entries"][name]['pages']
                            try:
                                transifex_dict["entries"][name].update(
                                    {"description": new_data['data']['description']['value']})
                            except KeyError:
                                transifex_dict["entries"][name].update(
                                    {"description": new_data['system']['description']['value']})

                    # Dla tabel
                    elif 'displayRoll' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        transifex_dict["entries"][name].update({"description": new_data['description']})
                        transifex_dict["entries"][name].update({"results": {}})
                        for result in new_data['results']:
                            result_name = f'{result["range"][0]}-{result["range"][1]}'
                            transifex_dict["entries"][name]['results'].update({result_name: result['text']})

                    # elif 'results' in keys:
                    #     transifex_dict["entries"].update({name: {}})
                    #     transifex_dict["entries"][name].update({"name": name})
                    #     transifex_dict["entries"][name].update({"description": new_data.get("description")})
                    #     transifex_dict["entries"][name].update({"results": {}})
                    #     try:
                    #         for result in new_data["results"]:
                    #             try:
                    #                 for id_result in data:
                    #                     if result == id_result["_id"]:
                    #                         transifex_dict["entries"][name]['results'].update(
                    #                             {f"{id_result['range'][0]}-{id_result['range'][1]}": id_result['text']})
                    #             except TypeError:
                    #                 pass
                    #     except KeyError:
                    #         pass

                    # Dla Kompendium
                    elif 'items' not in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        try:  # Dla efektów z dodatków
                            if not new_data['system']['description']['value'].startswith('<p>@Localize'):
                                transifex_dict["entries"][name].update(
                                    {"description": new_data['system']['description']['value']})
                        except KeyError:
                            pass

                    # Dla Dzienników (inna metoda)
                    if 'pages' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        transifex_dict["entries"][name].update({"pages": {}})
                        try:
                            for result in new_data['pages']:
                                for pages in data:
                                    try:
                                        if result == pages['_id']:
                                            transifex_dict["entries"][name]['pages'].update({pages['name']: {}})
                                            transifex_dict["entries"][name]['pages'][pages['name']].update(
                                                {"name": pages['name']})
                                            transifex_dict["entries"][name]['pages'][pages['name']].update(
                                                {"text": pages['text']['content']})
                                    except KeyError:
                                        pass
                        except KeyError:
                            pass

                    # ====================================================================================================
                    # ---GM Note---
                    try:
                        if type_system == 'pf2e-ranged-combat':
                            pass
                        else:
                            if new_data['system']['description']['gm']:
                                transifex_dict["entries"][name].update(
                                    {"gmNote": new_data['system']['description']['gm']})
                                flag.append('gm')
                    except KeyError:
                        pass

                    if 'gm' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "gmNote": "system.description.gm"
                            }
                        )

                    # ---Rules---
                    transifex_dict["entries"][name].update({"rules": {}})
                    rule_id = 0
                    try:
                        for rules in new_data['system']['rules']:
                            try:
                                if rules['text'] != '' and not rules['text'].startswith("PF2E") and not rules['text'].startswith("{item"):
                                    transifex_dict["entries"][name]["rules"].update({rule_id: {"text": rules['text']}})
                                    flag.append('rules')

                            except KeyError:
                                pass
                            try:
                                if rules['label'] != '' and not rules['label'].startswith("PF2E"):
                                    transifex_dict["entries"][name]["rules"].update(
                                        {rule_id: {"label": rules['label']}})
                                    flag.append('rules')

                            except KeyError:
                                pass
                            try:
                                if rules['choices'] != '':
                                    transifex_dict["entries"][name]["rules"].update({rule_id: {"choices": {}}})
                                    choice_id = 0
                                    try:
                                        if not rules.get('prompt').startswith("PF2E") :
                                            transifex_dict["entries"][name]["rules"][rule_id].update(
                                                {"prompt": rules['prompt']})
                                    except AttributeError:
                                        pass
                                    for choice in rules['choices']:
                                        try:
                                            if not choice['label'].startswith("PF2E"):
                                                transifex_dict["entries"][name]["rules"][rule_id]["choices"].update(
                                                    {choice_id: {"label": choice['label']}})
                                                flag.append('rules')
                                            choice_id += 1
                                        except TypeError:
                                            pass
                            except KeyError:
                                pass
                            rule_id += 1
                    except KeyError:
                        pass

                    if 'rules' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "rules": {
                                    "converter": "translateRules",
                                    "path": "system.rules"
                                }
                            }
                        )

                    # ---Trained Lore---
                    try:
                        if new_data['system']['trainedLore'] != "":
                            transifex_dict["entries"][name].update({"trainedLore": new_data['system']['trainedLore']})
                            flag.append('trainedLore')
                    except KeyError:
                        pass

                    if 'trainedLore' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "trainedLore": "system.trainedLore"
                            }
                        )

                    # ---Badges---
                    try:
                        transifex_dict["entries"][name].update({"badges": new_data['system']['badge']['labels']})
                        flag.append('badges')
                    except KeyError:
                        pass
                    except TypeError:
                        pass

                    if 'badges' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "badges": "system.badge.labels",
                            }
                        )

                    # ---Prerequisites---
                    try:
                        new_data = exclude_empty_prerequisites(new_data)
                        transifex_dict["entries"][name].update(
                            {"prerequisites": new_data['system']['prerequisites']['value']})
                        flag.append('prerequisites')
                    except KeyError:
                        pass

                    if 'prerequisites' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "prerequisites": "system.prerequisites.value",
                            }
                        )

                    # ---Hazard and NPC---
                    try:
                        if new_data['system']['details']['publicNotes'] != "":
                            transifex_dict["entries"][name].update(
                                {"publicNotes": new_data['system']['details']['publicNotes']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['privateNotes'] != "":
                            transifex_dict["entries"][name].update(
                                {"privateNotes": new_data['system']['details']['privateNotes']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['ac']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"acDetails": new_data['system']['attributes']['ac']['details']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['blurb'] != "":
                            transifex_dict["entries"][name].update({"blurb": new_data['system']['details']['blurb']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['allSaves']['value'] != "":
                            transifex_dict["entries"][name].update(
                                {"allSavesBonus": new_data['system']['attributes']['allSaves']['value']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['speed']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"speedsDetails": new_data['system']['attributes']['speed']['details']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['perception']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"sensesDetails": new_data['system']['perception']['details']})
                            flag.append('bestiary')
                    except (TypeError, KeyError) as e:
                        pass

                    try:
                        if new_data['system']['details']['languages']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"languagesDetails": new_data['system']['details']['languages']['details']})
                            flag.append('bestiary')
                    except (TypeError, KeyError) as e:
                        pass

                    if 'bestiary' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "publicNotes": "system.details.publicNotes",
                                "privateNotes": "system.details.privateNotes",
                                "acDetails": "system.attributes.ac.details",
                                "blurb": "system.details.blurb",
                                "hpDetails": "system.attributes.hp.details",
                                "allSavesBonus": "system.attributes.allSaves.value",
                                "speedsDetails": "system.attributes.speed.details",
                                "sensesDetails": "system.perception.details",
                                "languagesDetails": "system.details.languages.details"
                            }
                        )

                    try:
                        if new_data['system']['attributes']['hp']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"hpDetails": new_data['system']['attributes']['hp']['details']})
                            flag.append('hp')
                    except KeyError:
                        pass

                    if 'hp' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "hpDetails": "system.attributes.hp.details"
                            }
                        )

                    # ---Hazard---
                    try:
                        if new_data['system']['details']['description'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"descriptionHazard": new_data['system']['details']['description']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['disable'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"disable": new_data['system']['details']['disable']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['reset'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update({"reset": new_data['system']['details']['reset']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['routine'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"routine": new_data['system']['details']['routine']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['stealth']['details'] != "" and new_data[
                            'type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"stealth": new_data['system']['attributes']['stealth']['details']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    if 'hazard' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "descriptionHazard": "system.details.description",
                                "disable": "system.details.disable",
                                "reset": "system.details.reset",
                                "routine": "system.details.routine",
                                "stealth": "system.attributes.stealth.details",
                            }
                        )
                    # ---Vehicles---
                    try:
                        if new_data['system']['details']['description'] != "" and new_data['type'] == 'vehicle':
                            transifex_dict["entries"][name].update(
                                {"description": new_data['system']['details']['description']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['crew'] != "":
                            transifex_dict["entries"][name].update({"crew": new_data['system']['details']['crew']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['pilotingCheck'] != "":
                            transifex_dict["entries"][name].update(
                                {"pilotingCheck": new_data['system']['details']['pilotingCheck']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['speed'] != "":
                            transifex_dict["entries"][name].update({"speed": new_data['system']['details']['speed']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    if 'vehicles' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "description": "system.details.description",
                                "crew": "system.details.crew",
                                "pilotingCheck": "system.details.pilotingCheck",
                                "speed": "system.details.speed",
                            }
                        )

                    # === ITEMS ===
                    transifex_dict["entries"][name].update({"items": {}})
                    try:
                        for item in new_data['items']:
                            # Nazwanie klucza
                            if item['type'] in ['melee', 'ranged']:
                                type_name = f'strike-{item["system"]["weaponType"]["value"]}'
                            else:
                                type_name = item['type']
                            item_name = f'{type_name}->{item["name"]}'

                            # Jeśli akcja jest połączona z bronią, nie tłumacz
                            try:
                                propertly_link = True
                                if 'linkedWeapon' in item['flags']['pf2e']:
                                    for item2 in new_data['items']:
                                        if item2['flags']['core']['sourceId'].startswith('Compendium') and item2[
                                            '_id'] == \
                                                item['flags']['pf2e']['linkedWeapon']:
                                            propertly_link = False
                                            break
                                    if item['name'] == 'Shiv':
                                        propertly_link = True
                                    if propertly_link:
                                        transifex_dict["entries"][name]['items'].update({item_name: {
                                            "name": item['name']
                                        }})
                                    continue
                            except KeyError:
                                pass

                            # Jeśli zaklęcie, bierz z kompendium
                            if item['type'] == 'spell':
                                # transifex_dict["entries"][name]['items'].update({item_name: {
                                #     "name": "<Compendium>",
                                #     "id": item['_id']
                                # }})
                                continue

                            # Jeśli jest to Skill, sprawdź, czy to unikalna nazwa i czy są jakieś opcje
                            if item['type'] == 'lore':
                                if item['name'] not in LORE_NAMES:
                                    transifex_dict["entries"][name]['items'].update({item_name: {
                                        "name": item['name']
                                    }})
                                elif 'variants' in item['system'].keys():
                                    transifex_dict["entries"][name]['items'].update({item_name: {
                                        "skillVariants": {'0': {'label': item['system']['variants']['0']['label']}}}
                                    })
                                continue

                            # Jeśli przedmiot jest z istniejącej publikacji i nie jest przedmiotem z innego kompendium
                            try:
                                if (item['flags']['core']['sourceId'].startswith('Compendium')
                                        and item['system']['publication']['title'] != ""
                                        and '(' not in item['name'] and item['type'] != 'action'):
                                    continue
                            except KeyError:
                                pass

                            # Jeśli opis jest przetłumaczony, bierz tylko nazwę, w przeciwnym wypadku razem z opisem
                            if item['system']['description']['value'].startswith('<p>@Localize') or \
                                    item['system']['description']['value'] == "":
                                if item['name'] == 'Darkvision' or item['name'] == 'Low-Light Vision' or item[
                                    'name'] == 'Greater Darkvision':
                                    continue
                                transifex_dict["entries"][name]['items'].update({item_name: {
                                    "name": item['name']
                                }})
                            else:
                                transifex_dict["entries"][name]['items'].update({item_name: {
                                    "name": item['name'],
                                    "description": item['system']['description']['value']
                                }})

                            flag.append('items')
                    except KeyError:
                        pass
                    except TypeError:
                        pass

                    if 'items' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "items": {
                                    "converter": "translateActorItems",
                                    "path": "items"
                                },
                            }
                        )

                    # SPELLS =============================================================================================
                    if file == 'spells.json':
                        name = new_data["name"].strip()

                        # AreaDetail
                        try:
                            transifex_dict["entries"][name].update(
                                {"areadetails": new_data['system']['area']['details']})
                        except (KeyError, TypeError):
                            pass

                        # Cost
                        if new_data['system']['cost']['value'] != "":
                            transifex_dict["entries"][name].update({"cost": new_data['system']['cost']['value']})

                        # Duration
                        if new_data['system']['duration']['value'] != "":
                            transifex_dict["entries"][name].update(
                                {"duration": new_data['system']['duration']['value']})

                        # Range
                        if new_data['system']['range']['value'] != "":
                            transifex_dict["entries"][name].update({"range": new_data['system']['range']['value']})

                        # Requirements
                        if new_data['system']['requirements'] != "":
                            transifex_dict["entries"][name].update({"requirements": new_data['system']['requirements']})

                        # Target
                        if new_data['system']['target']['value'] != "":
                            transifex_dict["entries"][name].update({"target": new_data['system']['target']['value']})

                        # Time
                        if new_data['system']['time']['value'] != "":
                            transifex_dict["entries"][name].update({"time": new_data['system']['time']['value']})

                        # Primary check
                        try:
                            if new_data['system']['ritual']['primary']['check'] != "":
                                transifex_dict["entries"][name].update(
                                    {"primarycheck": new_data['system']['ritual']['primary']['check']})
                        except KeyError:
                            pass
                        except TypeError:
                            pass

                        # Secondary check
                        try:
                            if new_data['system']['ritual']['secondary']['checks'] != "":
                                transifex_dict["entries"][name].update(
                                    {"secondarycheck": new_data['system']['ritual']['secondary']['checks']})
                        except KeyError:
                            pass
                        except TypeError:
                            pass

                        # Heightening
                        try:
                            if new_data['system']['heightening']['levels'] != "":
                                transifex_dict["entries"][name].update({"heightening": {}})
                                for level in new_data['system']['heightening']['levels']:
                                    transifex_dict["entries"][name]["heightening"].update({level: {}})
                                    for type_system in new_data['system']['heightening']['levels'][level]:
                                        if type_system == 'damage' or type_system == 'area':
                                            continue
                                        transifex_dict["entries"][name]["heightening"][level].update(
                                            {type_system:
                                                 new_data['system']['heightening']['levels'][level][type_system][
                                                     'value']})
                                transifex_dict = remove_empty_values(transifex_dict)
                        except KeyError:
                            pass

                        # spellVariants
                        try:
                            if new_data['system']['overlays'] != "":
                                transifex_dict["entries"][name].update({"spellVariants": {}})
                                for overlays in new_data['system']['overlays']:
                                    try:
                                        if new_data['system']['overlays'][overlays]['name'] != "":
                                            transifex_dict["entries"][name]["spellVariants"].update({overlays: {}})
                                            transifex_dict["entries"][name]["spellVariants"][overlays].update(
                                                {"name": new_data['system']['overlays'][overlays]['name']})
                                    except KeyError:
                                        pass

                        except KeyError:
                            pass

                transifex_dict = remove_empty_values(transifex_dict)
                transifex_dict = remove_empty_values(transifex_dict)
                transifex_dict = remove_empty_values(transifex_dict)
                transifex_dict = sort_entries(transifex_dict)
                with open(new_name, "w", encoding='utf-8') as outfile:
                    json.dump(transifex_dict, outfile, ensure_ascii=False, indent=4)

                dict_key.append(f'{compendium.keys()}')


remove_folders_except_venv()
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Ścieżka do pliku z wersją systemu
# sys_url = "https://github.com/foundryvtt/pf2e/releases/latest/download/system.json"
#
# path, headers = urlretrieve(sys_url, 'system.json')
# version = json.loads(open('system.json', 'r', encoding='utf-8').read())["version"]
# zip_url = "https://github.com/foundryvtt/pf2e/releases/latest/download/json-assets.zip"
# extract_folder = 'pack'
# print()
# print("*** Wersja modułu PF2E: ", version, " ***")
#
# zip_filename = "json-assets.zip"
#
# if create_version_directory(version):
#     download_and_extract_zip(zip_url, zip_filename, extract_folder)
# else:
#     with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
#         zip_ref.extractall(extract_folder)

# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons0
# Ścieżka do pliku z wersją addon0
# add_0_url = "https://github.com/TikaelSol/starfinder-field-test/releases/latest/download/module.json"
#
# path_0, headers_0 = urlretrieve(add_0_url, 'module_0.json')
# version_0 = 'starfinder_0_' + json.loads(open('module_0.json', 'r', encoding='utf-8').read())["version"]
# zip_addons0_filename = "starfinder-field-test-for-pf2e.zip"
# zip_addons0 = 'https://github.com/TikaelSol/starfinder-field-test/releases/latest/download/starfinder-field-test-for-pf2e.zip'
# extract_folder = 'starfinder2e_0'
# print()
# print("*** Wersja dodatku_0 SF2E: ", version_0, " ***")
#
# if create_version_directory(version_0):
#     download_and_extract_zip(zip_addons0, zip_addons0_filename, extract_folder)
# else:
#     with zipfile.ZipFile(zip_addons0_filename, 'r') as zip_ref:
#         zip_ref.extractall(extract_folder)
#
# read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons1
# Ścieżka do pliku z wersją addon1
add_1_url = "https://github.com/reyzor1991/foundry-vtt-pf2e-action-support/releases/latest/download/module.json"

path_1, headers_1 = urlretrieve(add_1_url, 'module_1.json')
version_1 = 'addon_1_' + json.loads(open('module_1.json', 'r', encoding='utf-8').read())["version"]
zip_addons1_filename = "pf2e-action-support.zip"
zip_addons1 = 'https://github.com/reyzor1991/foundry-vtt-pf2e-action-support/releases/latest/download/pf2e-action-support.zip'
extract_folder = 'pack_addon_1'
print()
print("*** Wersja dodatku_1 PF2E: ", version_1, " ***")

if create_version_directory(version_1):
    download_and_extract_zip(zip_addons1, zip_addons1_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons1_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

convert_extension(fr'{extract_folder}\pf2e-action-support\packs', "action-support", "action-support")
convert_extension(fr'{extract_folder}\pf2e-action-support\packs', "action-support-macros", "action-support-macros")
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons2
# Ścieżka do pliku z wersją addon2
add_2_url = "https://github.com/JDCalvert/FVTT-PF2e-Ranged-Combat/releases/latest/download/module.json"

path_2, headers_2 = urlretrieve(add_2_url, 'module_2.json')
version_2 = 'addon_2_' + json.loads(open('module_2.json', 'r', encoding='utf-8').read())["version"]
zip_addons2_filename = "pf2e-ranged-combat.zip"
zip_addons2 = 'https://github.com/JDCalvert/FVTT-PF2e-Ranged-Combat/releases/latest/download/pf2e-ranged-combat.zip'
extract_folder = 'pack_addon_2'
print()
print("*** Wersja dodatku_2 PF2E: ", version_2, " *** ")

if create_version_directory(version_2):
    download_and_extract_zip(zip_addons2, zip_addons2_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons2_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons3
# Ścieżka do pliku z wersją addon3
add_3_url = "https://github.com/reyzor1991/foundry-vtt-pf2e-reaction/releases/latest/download/module.json"

path_3, headers_3 = urlretrieve(add_3_url, 'module_3.json')
version_3 = 'addon_3_' + json.loads(open('module_3.json', 'r', encoding='utf-8').read())["version"]
zip_addons3_filename = "pf2e-reaction.zip"
zip_addons3 = 'https://github.com/reyzor1991/foundry-vtt-pf2e-reaction/releases/latest/download/pf2e-reaction.zip'
extract_folder = 'pack_addon_3'
print()
print("*** Wersja dodatku_3 PF2E: ", version_3, " ***")

if create_version_directory(version_3):
    download_and_extract_zip(zip_addons3, zip_addons3_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons3_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

convert_extension(fr'{extract_folder}\pf2e-reaction\packs', "reaction-effects", "reaction-effects")
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons4
# Ścieżka do pliku z wersją addon4
add_4_url = "https://github.com/mysurvive/pf2e-thaum-vuln/releases/latest/download/module.json"

path_4, headers_4 = urlretrieve(add_4_url, 'module_4.json')
version_4 = 'addon_4_' + json.loads(open('module_4.json', 'r', encoding='utf-8').read())["version"]
zip_addons4_filename = "pf2e-thaum-vuln.zip"
zip_addons4 = 'https://github.com/mysurvive/pf2e-thaum-vuln/releases/latest/download/module.zip'
extract_folder = 'pack_addon_4'
print()
print("*** Wersja dodatku_4 PF2E: ", version_4, " ***")

if create_version_directory(version_4):
    download_and_extract_zip(zip_addons4, zip_addons4_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons4_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons5
# Ścieżka do pliku z wersją addon5
add_5_url = "https://github.com/silvative/pf2e-exploration-effects/releases/latest/download/module.json"

path_5, headers_5 = urlretrieve(add_5_url, 'module_5.json')
version_5 = 'addon_5_' + json.loads(open('module_5.json', 'r', encoding='utf-8').read())["version"]
zip_addons5_filename = "pf2e-exploration-effects.zip"
zip_addons5 = 'https://github.com/silvative/pf2e-exploration-effects/releases/latest/download/module.zip'
extract_folder = 'pack_addon_5'
print()
print("*** Wersja dodatku_5 PF2E: ", version_5, " ***")

if create_version_directory(version_5):
    download_and_extract_zip(zip_addons5, zip_addons5_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons5_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons6
# Ścieżka do pliku z wersją addon6
add_6_url = "https://github.com/ChasarooniZ/pf2e-item-activations/releases/latest/download/module.json"

path_6, headers_6 = urlretrieve(add_6_url, 'module_6.json')
version_6 = 'addon_6_' + json.loads(open('module_6.json', 'r', encoding='utf-8').read())["version"]
zip_addons6_filename = "pf2e-item-activations.zip"
zip_addons6 = 'https://github.com/ChasarooniZ/pf2e-item-activations/releases/latest/download/module.zip'
extract_folder = 'pack_addon_6'
print()
print("*** Wersja dodatku_6 PF2E: ", version_6, " ***")

if create_version_directory(version_6):
    download_and_extract_zip(zip_addons6, zip_addons6_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons6_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons7
# Ścieżka do pliku z wersją addon7
add_7_url = "https://github.com/jmerlin-nerd/elemental-ammunition-for-pf2e/releases/latest/download/module.json"

path_7, headers_7 = urlretrieve(add_7_url, 'module_7.json')
version_7 = 'addon_7_' + json.loads(open('module_7.json', 'r', encoding='utf-8').read())["version"]
zip_addons7_filename = "elemental-ammunition-for-pf2e.zip"
zip_addons7 = 'https://github.com/jmerlin-nerd/elemental-ammunition-for-pf2e/releases/latest/download/module.zip'
extract_folder = 'pack_addon_7'
print()
print("*** Wersja dodatku_7 PF2E: ", version_7, " ***")

if create_version_directory(version_7):
    download_and_extract_zip(zip_addons7, zip_addons7_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons7_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons8
# Ścieżka do pliku z wersją addon8
add_8_url = "https://github.com/kristkos/KCTG-2e/releases/latest/download/module.json"

path_8, headers_8 = urlretrieve(add_8_url, 'module_8.json')
version_8 = 'addon_8_' + json.loads(open('module_8.json', 'r', encoding='utf-8').read())["version"]
zip_addons8_filename = "kctg-2e.zip"
zip_addons8 = 'https://github.com/kristkos/KCTG-2e/releases/latest/download/kctg-2e.zip'
extract_folder = 'pack_addon_8'
print()
print("*** Wersja dodatku_8 PF2E: ", version_8, " ***")

if create_version_directory(version_8):
    download_and_extract_zip(zip_addons8, zip_addons8_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons8_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons9
# Ścieżka do pliku z wersją addon9
add_9_url = "https://raw.githubusercontent.com/TikaelSol/PF2e-Animal-Companions/master/module.json"

path_9, headers_9 = urlretrieve(add_9_url, 'module_9.json')
version_9 = 'addon_9_' + json.loads(open('module_9.json', 'r', encoding='utf-8').read())["version"]
zip_addons9_filename = "pf2e-animal-companions.zip"
zip_addons9 = 'https://github.com/TikaelSol/PF2e-Animal-Companions/releases/latest/download/module.zip'
extract_folder = 'pack_addon_9'
print()
print("*** Wersja dodatku_9 PF2E: ", version_9, " ***")

if create_version_directory(version_9):
    download_and_extract_zip(zip_addons9, zip_addons9_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons9_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

source_folder = fr'{extract_folder}/build/packs'
target_folder = fr'{extract_folder}/packs'

for file_name in os.listdir(source_folder):
    source_path = os.path.join(source_folder, file_name)
    target_path = os.path.join(target_folder, file_name)

    if os.path.isfile(source_path):
        shutil.move(source_path, target_path)
    elif os.path.isdir(source_path):
        shutil.move(source_path, target_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons10
# Ścieżka do pliku z wersją addon10
add_10_url = "https://www.dropbox.com/scl/fi/hopwdnv911f7332tlu7ss/module.json?rlkey=udckjm1m1lk99ehfea930lesb&st=q3kuxm9t&dl=1"

path_10, headers_10 = urlretrieve(add_10_url, 'module_10.json')
version_10 = 'addon_10_' + json.loads(open('module_10.json', 'r', encoding='utf-8').read())["version"]
zip_addons10_filename = "pf2e-macros.zip"
zip_addons10 = 'https://www.dropbox.com/scl/fi/5r9mdw8r1gw5r3cxu2imz/pf2e-macros.zip?rlkey=l34j1isit0b89qujmqez7aehj&st=7qrt3kr3&dl=1'
extract_folder = 'pack_addon_10'
print()
print("*** Wersja dodatku_10 PF2E: ", version_10, " ***")

if create_version_directory(version_10):
    download_and_extract_zip(zip_addons10, zip_addons10_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons10_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\pf2e-macros\packs', fr'{extract_folder}\pf2e-macros\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons11
# Ścieżka do pliku z wersją addon11
add_11_url = "https://github.com/JDCalvert/pf2e-kineticists-companion/releases/latest/download/module.json"

path_11, headers_11 = urlretrieve(add_11_url, 'module_11.json')
version_11 = 'addon_11_' + json.loads(open('module_11.json', 'r', encoding='utf-8').read())["version"]
zip_addons11_filename = "pf2e-kineticists-companion.zip"
zip_addons11 = 'https://github.com/JDCalvert/pf2e-kineticists-companion/releases/latest/download/pf2e-kineticists-companion.zip'
extract_folder = 'pack_addon_11'
print()
print("*** Wersja dodatku_11 PF2E: ", version_11, " ***")

if create_version_directory(version_11):
    download_and_extract_zip(zip_addons11, zip_addons11_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons11_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons12
# Ścieżka do pliku z wersją addon12
add_12_url = "https://github.com/Suldrun45/pf2e-specific-familiars/releases/latest/download/module.json"

path_12, headers_12 = urlretrieve(add_12_url, 'module_12.json')
version_12 = 'addon_12_' + json.loads(open('module_12.json', 'r', encoding='utf-8').read())["version"]
zip_addons12_filename = "pf2e-specific-familiars.zip"
zip_addons12 = 'https://github.com/Suldrun45/pf2e-specific-familiars/releases/latest/download/pf2e-specific-familiars.zip'
extract_folder = 'pack_addon_12'
print()
print("*** Wersja dodatku_12 PF2E: ", version_12, " ***")

if create_version_directory(version_12):
    download_and_extract_zip(zip_addons12, zip_addons12_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons12_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

move_files(fr'{extract_folder}/pf2e-specific-familiars/packs', fr'{extract_folder}/packs')

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons13
# Ścieżka do pliku z wersją addon13
add_13_url = "https://github.com/7H3LaughingMan/pf2e-assistant/releases/latest/download/module.json"

path_13, headers_13 = urlretrieve(add_13_url, 'module_13.json')
version_13 = 'addon_13_' + json.loads(open('module_13.json', 'r', encoding='utf-8').read())["version"]
zip_addons13_filename = "pf2e-assistant.zip"
zip_addons13 = 'https://github.com/7H3LaughingMan/pf2e-assistant/releases/latest/download/module.zip'
extract_folder = 'pack_addon_13'
print()
print("*** Wersja dodatku_13 PF2E: ", version_13, " ***")

if create_version_directory(version_13):
    download_and_extract_zip(zip_addons13, zip_addons13_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons13_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')

# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons14
# Ścieżka do pliku z wersją addon14
add_14_url = "https://www.dropbox.com/scl/fi/7llzr0iqqfv7r0mnpfaoc/module.json?rlkey=crj4cmuz7twfu85tgmh3ysa08&dl=1"

path_14, headers_14 = urlretrieve(add_14_url, 'module_14.json')
version_14 = 'addon_14_' + json.loads(open('module_14.json', 'r', encoding='utf-8').read())["version"]
zip_addons14_filename = "pf2e-summons-helper.zip"
zip_addons14 = 'https://www.dropbox.com/scl/fi/dzsizuvhxqu5hs4mlry82/pf2e-summons-helper.zip?rlkey=s9gn1u35f1vzwz8fmmblmk0ld&dl=1'
extract_folder = 'pack_addon_14'
print()
print("*** Wersja dodatku_14 PF2E: ", version_14, " ***")

if create_version_directory(version_14):
    download_and_extract_zip(zip_addons14, zip_addons14_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons14_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

convert_extension(fr'{extract_folder}\pf2e-summons-helper\packs', "summons-effect", "summons-effect")
convert_extension(fr'{extract_folder}\pf2e-summons-helper\packs', "summons-macros", "summons-macros")
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons15
# Ścieżka do pliku z wersją addon15
add_15_url = "https://github.com/reyzor1991/pf2e-initiative-effect/releases/latest/download/module.json"

path_15, headers_15 = urlretrieve(add_15_url, 'module_15.json')
version_15 = 'addon_15_' + json.loads(open('module_15.json', 'r', encoding='utf-8').read())["version"]
zip_addons15_filename = "pf2e-initiative-effect.zip"
zip_addons15 = 'https://github.com/reyzor1991/pf2e-initiative-effect/releases/latest/download/pf2e-initiative-effect.zip'
extract_folder = 'pack_addon_15'
print()
print("*** Wersja dodatku_15 PF2E: ", version_15, " ***")

if create_version_directory(version_15):
    download_and_extract_zip(zip_addons15, zip_addons15_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons15_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

convert_extension(fr'{extract_folder}\pf2e-initiative-effect\packs', "initiative-effect", "initiative-effect")
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons16
# Ścieżka do pliku z wersją addon16
add_16_url = "https://github.com/TheErikkuBlade/pf2e-relics/releases/latest/download/module.json"

path_16, headers_16 = urlretrieve(add_16_url, 'module_16.json')
version_16 = 'addon_16_' + json.loads(open('module_16.json', 'r', encoding='utf-8').read())["version"]
zip_addons16_filename = "pf2e-relics.zip"
zip_addons16 = 'https://github.com/TheErikkuBlade/pf2e-relics/releases/latest/download/pf2e-relics.zip'
extract_folder = 'pack_addon_16'
print()
print("*** Wersja dodatku_16 PF2E: ", version_16, " ***")

if create_version_directory(version_16):
    download_and_extract_zip(zip_addons16, zip_addons16_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons16_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons17
# Ścieżka do pliku z wersją addon17
add_17_url = "https://github.com/BernhardPosselt/pf2e-kingmaker-tools/releases/latest/download/module.json"

path_17, headers_17 = urlretrieve(add_17_url, 'module_17.json')
version_17 = 'addon_17_' + json.loads(open('module_17.json', 'r', encoding='utf-8').read())["version"]
zip_addons17_filename = "pf2e-kingmaker-tools.zip"
zip_addons17 = 'https://github.com/BernhardPosselt/pf2e-kingmaker-tools/releases/latest/download/release.zip'
extract_folder = 'pack_addon_17'
print()
print("*** Wersja dodatku_17 PF2E: ", version_17, " ***")

if create_version_directory(version_17):
    download_and_extract_zip(zip_addons17, zip_addons17_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons17_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

move_files(fr'{extract_folder}/pf2e-kingmaker-tools/packs', fr'{extract_folder}/packs')
read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons18
# Ścieżka do pliku z wersją addon18
add_18_url = "https://github.com/FreedomIronbullet/pf2e-variant-cantrips/releases/latest/download/module.json"

path_18, headers_18 = urlretrieve(add_18_url, 'module_18.json')
version_18 = 'addon_18_' + json.loads(open('module_18.json', 'r', encoding='utf-8').read())["version"]
zip_addons18_filename = "pf2e-variant-cantrips.zip"
zip_addons18 = 'https://github.com/FreedomIronbullet/pf2e-variant-cantrips/releases/latest/download/module.zip'
extract_folder = 'pack_addon_18'
print()
print("*** Wersja dodatku_18 PF2E: ", version_18, " ***")

if create_version_directory(version_18):
    download_and_extract_zip(zip_addons18, zip_addons18_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_addons18_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

move_files(fr'{extract_folder}/pf2e-variant-cantrips/packs', fr'{extract_folder}/packs')
read_leveldb_to_json(fr'{extract_folder}\packs', fr'{extract_folder}\output')
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===

# folder = 'pack'
# process_files(folder, version, 'system')
print('\n*** KONWERSJA ***\n')

# folder = r'starfinder2e_0/output'
# process_files(folder, version_0, "starfinder-field-test-for-pf2e")

folder = r'pack_addon_1/pf2e-action-support/packs'
process_files(folder, version_1, 'pf2e-action-support')

folder = r'pack_addon_2/output'
process_files(folder, version_2, "pf2e-ranged-combat")

folder = r'pack_addon_3/pf2e-reaction/packs'
process_files(folder, version_3, "pf2e-reaction")

folder = r'pack_addon_4/output'
process_files(folder, version_4, "pf2e-thaum-vuln")

folder = r'pack_addon_5/output'
process_files(folder, version_5, "pf2e-exploration-effects")

folder = r'pack_addon_6/output'
process_files(folder, version_6, "pf2e-item-activations")

folder = r'pack_addon_7/output'
process_files(folder, version_7, "elemental-ammunition-for-pf2e")

folder = r'pack_addon_8/output'
process_files(folder, version_8, "kctg-2e")

folder = r'pack_addon_9/output'
process_files(folder, version_9, "pf2e-animal-companions")

folder = r'pack_addon_10/pf2e-macros/output'
process_files(folder, version_10, "pf2e-macros")

folder = r'pack_addon_11/output'
process_files(folder, version_11, "pf2e-kineticists-companion")

folder = r'pack_addon_12/output'
process_files(folder, version_12, "pf2e-specific-familiars")

folder = r'pack_addon_13/output'
process_files(folder, version_13, "pf2e-assistant")

folder = r'pack_addon_14/pf2e-summons-helper/packs'
process_files(folder, version_14, 'pf2e-summons-helper')

folder = r'pack_addon_15/pf2e-initiative-effect/packs'
process_files(folder, version_15, 'pf2e-initiative-effect')

folder = r'pack_addon_16/output'
process_files(folder, version_16, "pf2e-relics")

folder = r'pack_addon_17/output'
process_files(folder, version_17, "pf2e-kingmaker-tools")

folder = r'pack_addon_18/output'
process_files(folder, version_18, "pf2e-variant-cantrips")

copy_addon_folders()
clean()
