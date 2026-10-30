from uuid import uuid4

from app.client import SampleApisCoffeeClient
from app.exceptions import CoffeeApiError, CoffeeNotFoundError


def check_fields(actual: dict[str, object], expected: dict[str, object]) -> None:
    """Проверяет, что все поля из expected в actual совпадают."""
    for field, value in expected.items():
        if actual.get(field) != value:
            raise ValueError(
                f"Поле '{field}': ожидалось {value!r}, получено {actual.get(field)!r}"
            )


def main() -> int:
    client = SampleApisCoffeeClient()
    marker = uuid4().hex[:8]
    created_id = None
    stage = "начало"
    try:
        stage = "GET список"
        print("1. GET: получаем список горячих напитков")
        drinks = client.list_drinks()
        print(f"   Найдено напитков: {len(drinks)}")

        stage = "POST"
        print("2. POST: создаём новый напиток")
        new_drink = {
            "title": f"Group coffee {marker}",
            "description": "Hot drink",
            "ingredients": ["Water", "Coffee"],
            "image": "https://example.com/coffee.jpg",
        }
        created = client.create_drink(new_drink)
        # Сразу запоминаем id, чтобы finally мог удалить запись при любой ошибке.
        created_id = created.get("id")
        if created_id is None:
            raise ValueError("В ответе POST нет id")
        print(f"   Создан напиток id={created_id}")

        stage = "GET после POST"
        print("3. GET: читаем созданный напиток и сравниваем поля")
        check_fields(client.get_drink(created_id), new_drink)
        print("   Поля совпадают с отправленными")

        stage = "PUT"
        print("4. PUT: полностью заменяем данные")
        replaced = {
            "title": f"Replaced coffee {marker}",
            "description": "Fully replaced",
            "ingredients": ["Espresso"],
            "image": "https://example.com/replaced.jpg",
        }
        client.replace_drink(created_id, replaced)
        check_fields(client.get_drink(created_id), replaced)
        print("   Все заменённые поля подтверждены повторным GET")

        stage = "PATCH"
        print("5. PATCH: меняем только описание")
        changes = {"description": "Patched only"}
        client.update_drink(created_id, changes)
        after_patch = client.get_drink(created_id)
        check_fields(after_patch, changes)
        # Остальные поля должны сохраниться после PATCH.
        check_fields(
            after_patch,
            {key: value for key, value in replaced.items() if key != "description"},
        )
        print("   Описание изменилось, остальные поля сохранились")

        stage = "DELETE"
        print("6. DELETE: удаляем напиток")
        client.delete_drink(created_id)
        try:
            client.get_drink(created_id)
        except CoffeeNotFoundError:
            print("   GET после удаления вернул ожидаемый 404")
        else:
            raise ValueError("Напиток всё ещё доступен после DELETE")
        created_id = None  # удаление подтверждено, чистить в finally нечего

        print("Сценарий выполнен успешно")
    except (CoffeeApiError, ValueError) as error:
        print(f"Ошибка на этапе «{stage}»: {error}. Метка группы: {marker}")
        if stage == "POST":
            # После сбоя POST (например, тайм-аута) неизвестно, создалась ли запись.
            # POST не повторяем: проверьте вручную по метке.
            print(
                "   Результат создания неизвестен. POST не повторяется. "
                f"Проверьте вручную: GET /coffee/hot?title_like={marker}"
            )
        return 1
    finally:
        if created_id is not None:
            try:
                client.delete_drink(created_id)
            except CoffeeNotFoundError:
                pass
            except CoffeeApiError as error:
                print(f"Не удалось удалить id={created_id}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())