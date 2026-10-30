"""
Описание запроса создания горячего кофе
---------------------------------------

Метод и URL
    POST https://api.sampleapis.com/coffee/hot
    (базовый URL задаётся в конструкторе клиента, в методах не дублируется).

Заголовки
    Content-Type: application/json — обязателен. Без него сервер не разбирает
    тело как JSON и отвечает 400. Библиотека requests ставит этот заголовок
    сама, если передать тело через параметр ``json=``.

Тело запроса (JSON-объект)
    title        string         обязательное  название напитка
    description  string         обязательное  описание
    ingredients  array[string]  обязательное  список ингредиентов
    image        string         обязательное  ссылка на картинку
    id           —              НЕ передаём   выдаёт сервер

    Все четыре поля обязательны: если какого-то нет, сервер отвечает 400
    (в ответе есть ``message``, ``expected`` и ``received``).
    Типы и значения сервер не проверяет (пустые строки, число вместо
    строки проходят), лишние поля сохраняются.

Что задаёт клиент, что создаёт сервер
    Клиент:  title (с уникальной меткой группы), description, ingredients, image.
    Сервер:  id (максимальный числовой id + 1). Если передать id в теле, сервер
             возьмёт его, поэтому клиент id в POST не отправляет.

Успешный ответ
    Статус 201 (клиент принимает также 200), Content-Type: application/json,
    тело — созданный объект целиком, вместе с id, назначенным сервером.
    Этот id используется дальше для GET / PUT / PATCH / DELETE.

Что подтверждено запросами к API, а что проверяется только в клиенте
    Подтверждено запросами к API: обязательность четырёх полей, отказ (400)
    при неверном Content-Type и при некорректном JSON, id выдаёт сервер,
    статус 201 и форма ответа.
    Только в клиенте: проверка статуса и Content-Type ответа до разбора JSON,
    проверка, что ответ списка — массив, а ответ напитка — объект.
    Содержимое полей (типы, пустые строки) клиент не валидирует.

Особенности других методов
    GET несуществующего id           -> 404 и тело {}
    PUT                              -> 200, нужны все поля (как у POST)
    PATCH                            -> 200, только известные поля, не пустой {}
    DELETE                           -> 200 и тело {} (а не 204)
"""

import requests

from app.exceptions import CoffeeApiError, CoffeeNotFoundError

JsonObject = dict[str, object]

# Статусы, которые считаем успешными для каждого HTTP-метода.
_SUCCESS_STATUSES: dict[str, set[int]] = {
    "GET": {200},
    "POST": {200, 201},
    "PUT": {200},
    "PATCH": {200},
    "DELETE": {200, 204},
}


class SampleApisCoffeeClient:
    def __init__(
        self,
        base_url: str = "https://api.sampleapis.com/coffee/hot",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_drinks(self) -> list[JsonObject]:
        response = self._request("GET")
        data = self._parse_json(response)
        if not isinstance(data, list):
            raise CoffeeApiError("Ожидался JSON-массив напитков")
        return data

    def get_drink(self, drink_id: int) -> JsonObject:
        response = self._request("GET", f"/{drink_id}")
        return self._parse_object(response)

    def create_drink(self, payload: JsonObject) -> JsonObject:
        response = self._request("POST", payload=payload)
        return self._parse_object(response)

    def replace_drink(
        self,
        drink_id: int,
        payload: JsonObject,
    ) -> JsonObject:
        response = self._request("PUT", f"/{drink_id}", payload)
        return self._parse_object(response)

    def update_drink(
        self,
        drink_id: int,
        changes: JsonObject,
    ) -> JsonObject:
        response = self._request("PATCH", f"/{drink_id}", changes)
        return self._parse_object(response)

    def delete_drink(self, drink_id: int) -> None:
        # Тело ответа на DELETE не используем: успех определяется статусом.
        self._request("DELETE", f"/{drink_id}")

    def _request(
        self,
        method: str,
        path: str = "",
        payload: JsonObject | None = None,
    ) -> requests.Response:
        """Единая точка HTTP-логики: URL, тайм-аут, сеть и проверка статуса."""
        url = f"{self._base_url}{path}"
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                timeout=self._timeout,
            )
        except requests.RequestException as error:
            # Timeout, ConnectionError и прочие сетевые сбои.
            raise CoffeeApiError(
                f"{method} {url}: сетевая ошибка ({type(error).__name__}: {error})"
            ) from error

        # Статус проверяем ДО того, как трогаем тело ответа.
        if response.status_code == 404:
            raise CoffeeNotFoundError(f"{method} {url}: ресурс не найден (404)")
        if response.status_code not in _SUCCESS_STATUSES.get(method, {200}):
            raise CoffeeApiError(
                f"{method} {url}: неожиданный статус {response.status_code}"
            )
        return response

    @staticmethod
    def _parse_json(response: requests.Response) -> object:
        """Проверяет Content-Type и разбирает JSON, не пропуская чужие ошибки."""
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise CoffeeApiError(
                f"Ожидался JSON, получен Content-Type: {content_type or 'не указан'}"
            )
        try:
            return response.json()
        except ValueError as error:
            raise CoffeeApiError("Ответ не является корректным JSON") from error

    def _parse_object(self, response: requests.Response) -> JsonObject:
        data = self._parse_json(response)
        if not isinstance(data, dict):
            raise CoffeeApiError("Ожидался JSON-объект")
        return data