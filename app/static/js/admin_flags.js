document.addEventListener("DOMContentLoaded", function () {
    // Открытие модального окна для добавления флага
    document.getElementById("add-flag-button").addEventListener("click", function () {
        document.getElementById("modal-title").textContent = "Добавить флаг";
        document.getElementById("flag-form").reset();
        document.getElementById("challenge-id").value = "";
        document.getElementById("flag-modal").style.display = "block";
    });

    // Открытие модального окна для редактирования флага
    document.querySelectorAll(".edit-flag-button").forEach(button => {
        button.addEventListener("click", function () {
            const challengeId = this.getAttribute("data-challenge-id");
            const row = document.querySelector(`tr[data-challenge-id="${challengeId}"]`);

            document.getElementById("modal-title").textContent = "Редактировать флаг";
            document.getElementById("challenge-id").value = challengeId;
            document.getElementById("title").value = row.cells[0].textContent;
            document.getElementById("description").value = row.cells[1].textContent;
            document.getElementById("flag").value = row.cells[2].textContent;
            document.getElementById("points").value = row.cells[3].textContent;
            document.getElementById("category").value = row.cells[4].textContent;
            document.getElementById("flag-modal").style.display = "block";
        });
    });

    // Закрытие модального окна
    document.querySelector(".close").addEventListener("click", function () {
        document.getElementById("flag-modal").style.display = "none";
    });

    // Обработка отправки формы
    document.getElementById("flag-form").addEventListener("submit", function (event) {
        event.preventDefault();

        const challengeId = document.getElementById("challenge-id").value;
        const title = document.getElementById("title").value;
        const description = document.getElementById("description").value;
        const flag = document.getElementById("flag").value;
        const points = document.getElementById("points").value;
        const category = document.getElementById("category").value;

        const url = challengeId ? `/admin/edit_flag/${challengeId}` : "/admin/add_flag";
        const method = "POST";

        fetch(url, {
            method: method,
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ title, description, flag, points, category }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload(); // Перезагружаем страницу
            } else {
                alert("Ошибка: " + data.message);
            }
        })
        .catch(error => {
            console.error("Ошибка при отправке запроса:", error);
            alert("Ошибка при сохранении флага.");
        });
    });

    // Удаление флага
    document.querySelectorAll(".delete-flag-button").forEach(button => {
        button.addEventListener("click", function () {
            const challengeId = this.getAttribute("data-challenge-id");

            if (confirm("Вы уверены, что хотите удалить этот флаг?")) {
                fetch(`/admin/delete_flag/${challengeId}`, {
                    method: "POST",
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload(); // Перезагружаем страницу
                    } else {
                        alert("Ошибка: " + data.message);
                    }
                })
                .catch(error => {
                    console.error("Ошибка при отправке запроса:", error);
                    alert("Ошибка при удалении флага.");
                });
            }
        });
    });
});
