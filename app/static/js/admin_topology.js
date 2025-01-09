document.addEventListener("DOMContentLoaded", function () {
    // Получаем данные из атрибута data-topology
    const topologyDataElement = document.getElementById("topology-data");
    const rawData = topologyDataElement.getAttribute("data-topology");

    // Получаем пути к изображениям из атрибутов
    const nodeImages = {
        server: topologyDataElement.getAttribute("data-server-image"),
        workstation: topologyDataElement.getAttribute("data-workstation-image"),
        switch: topologyDataElement.getAttribute("data-switch-image"),
        router: topologyDataElement.getAttribute("data-router-image"),
        firewall: topologyDataElement.getAttribute("data-firewall-image"),
        zone1: topologyDataElement.getAttribute("data-zone1-image"),
        zone2: topologyDataElement.getAttribute("data-zone2-image"),
        ARM: topologyDataElement.getAttribute("data-server-image") // Используем изображение сервера для ARM
    };

    // Парсим JSON-строку в объект JavaScript
    let topologyData;
    try {
        topologyData = JSON.parse(rawData);
        console.log("Parsed data:", topologyData);
    } catch (error) {
        console.error("Error parsing JSON:", error);
        return;
    }

    // Проверка данных
    if (!topologyData || typeof topologyData !== "object") {
        console.error("Некорректные данные топологии: данные не являются объектом", topologyData);
        return;
    }

    if (!Array.isArray(topologyData.nodes)) {
        console.error("Некорректные данные узлов: nodes не является массивом", topologyData.nodes);
        return;
    }

    if (!Array.isArray(topologyData.links)) {
        console.error("Некорректные данные связей: links не является массивом", topologyData.links);
        return;
    }

    // Инициализация контейнера
    const container = document.getElementById("topology-container");
    if (!container) {
        console.error("Контейнер для топологии не найден!");
        return;
    }

    // Инициализация узлов и связей
    const nodes = new vis.DataSet(topologyData.nodes.map(node => {
        const nodeConfig = {
            id: node.id,
            label: node.domain || node.id, // Используем domain как label, если он есть
            x: node.x || Math.random() * 500, // Случайная позиция по X, если не указана
            y: node.y || Math.random() * 500, // Случайная позиция по Y, если не указана
            type: node.type,
            shape: "image",
            image: nodeImages[node.type] || "https://via.placeholder.com/50/000000/FFFFFF?text=Node", // Используем изображение по типу узла
            size: 30,
            description: node.description || "Нет описания",
            interfaces: node.interfaces || []
        };

        // Увеличиваем размер и добавляем класс для зон
        if (node.type === "zone1" || node.type === "zone2") {
            nodeConfig.size = 50; // Увеличиваем размер зон
            nodeConfig.class = "zone-node"; // Добавляем класс для стилей
        }

        return nodeConfig;
    }));

    const edges = new vis.DataSet(topologyData.links.map(link => ({
        id: link.id || `${link.source}-${link.target}`, // Генерируем ID, если его нет
        from: link.source,
        to: link.target,
        smooth: false
    })));

    // Настройки сети
    const options = {
        physics: false,
        edges: {
            smooth: false,
            arrows: {
                to: { enabled: true, scaleFactor: 0.5 }
            },
            color: {
                color: "#2B7CE9",
                highlight: "#2B7CE9",
                hover: "#2B7CE9",
                inherit: false
            },
            width: 2
        },
        nodes: {
            borderWidth: 2,
            color: {
                border: "#2B7CE9",
                background: "#FFFFFF",
                highlight: {
                    border: "#2B7CE9",
                    background: "#D2E5FF"
                },
                hover: {
                    border: "#2B7CE9",
                    background: "#D2E5FF"
                }
            },
            font: {
                color: "#000000",
                size: 14,
                face: "Arial"
            },
            scaling: {
                min: 1,
                max: 1
            }
        }
    };

    // Создаем сеть
    const data = { nodes: nodes, edges: edges };
    const network = new vis.Network(container, data, options);

    // Логика для модального окна добавления узла
    const addNodeModal = document.getElementById("add-node-modal");
    const addNodeButton = document.getElementById("add-node-button");
    const closeAddNodeModal = addNodeModal.querySelector(".close");
    const nodeForm = document.getElementById("node-form");
    const interfacesContainer = document.getElementById("interfaces-container");
    const addInterfaceButton = document.getElementById("add-interface-button");

    // Открываем модальное окно добавления узла
    addNodeButton.addEventListener("click", function () {
        selectedNodeId = null; // Сбрасываем selectedNodeId для создания нового узла
        addNodeModal.style.display = "block";
    });

    // Закрываем модальное окно добавления узла
    closeAddNodeModal.addEventListener("click", function () {
        addNodeModal.style.display = "none";
    });

    // Добавляем новый интерфейс
    addInterfaceButton.addEventListener("click", function () {
        const interfaceCount = document.querySelectorAll(".interface").length + 1;
        const newInterface = document.createElement("div");
        newInterface.className = "interface";
        newInterface.innerHTML = `
            <label>Интерфейс ${interfaceCount}:</label>
            <input type="text" placeholder="Имя интерфейса" class="interface-name" required>
            <input type="text" placeholder="IP-адрес" class="interface-ip" required>
        `;
        interfacesContainer.appendChild(newInterface);
    });

    // Обработка отправки формы добавления/редактирования узла
    nodeForm.addEventListener("submit", function (event) {
        event.preventDefault();

        // Получаем данные из формы
        const nodeType = document.getElementById("node-type").value;
        const nodeName = document.getElementById("node-name").value;
        const nodeDescription = document.getElementById("node-description").value; // Получаем описание
        const interfaces = [];
        document.querySelectorAll(".interface").forEach(interfaceElement => {
            const interfaceName = interfaceElement.querySelector(".interface-name").value;
            const interfaceIp = interfaceElement.querySelector(".interface-ip").value;
            interfaces.push({ name: interfaceName, ip: interfaceIp });
        });

        if (selectedNodeId !== null) {
            // Редактируем существующий узел
            nodes.update({
                id: selectedNodeId,
                label: nodeName,
                type: nodeType,
                description: nodeDescription, // Обновляем описание
                interfaces: interfaces
            });

            console.log(`Узел с ID ${selectedNodeId} обновлён.`, {
                type: nodeType,
                name: nodeName,
                description: nodeDescription,
                interfaces: interfaces
            });
        } else {
            // Создаем новый узел
            const newNodeId = nodes.length + 1; // Генерируем уникальный ID для нового узла
            nodes.add({
                id: newNodeId,
                label: nodeName,
                x: Math.random() * 500,
                y: Math.random() * 500,
                shape: "image",
                image: nodeImages[nodeType],
                size: 30,
                level: 2,
                type: nodeType,
                description: nodeDescription, // Добавляем описание
                interfaces: interfaces
            });

            console.log(`Добавлен новый узел с ID: ${newNodeId}`, {
                type: nodeType,
                name: nodeName,
                description: nodeDescription,
                interfaces: interfaces
            });
        }

        // Закрываем модальное окно
        addNodeModal.style.display = "none";

        // Очищаем форму
        nodeForm.reset();
        interfacesContainer.innerHTML = `
            <div class="interface">
                <label>Интерфейс 1:</label>
                <input type="text" placeholder="Имя интерфейса" class="interface-name" required>
                <input type="text" placeholder="IP-адрес" class="interface-ip" required>
            </div>
        `;

        // Сбрасываем selectedNodeId
        selectedNodeId = null;
    });

    // Логика для добавления связей
    const addEdgeButton = document.getElementById("add-edge-button");
    let isAddingEdge = false; // Флаг для отслеживания режима добавления связи

    // Включаем/выключаем режим добавления связи
    addEdgeButton.addEventListener("click", function () {
        isAddingEdge = !isAddingEdge; // Переключаем режим
        addEdgeButton.textContent = isAddingEdge ? "Отменить добавление связи" : "Добавить связь";

        if (isAddingEdge) {
            network.addEdgeMode(); // Включаем режим добавления связи
            network.off("click"); // Отключаем обработчик клика на узлы
        } else {
            network.disableEditMode(); // Выключаем режим редактирования
            network.on("click", handleNodeClick); // Включаем обработчик клика на узлы
        }
    });

    // Обработчик события создания связи
    network.on("addEdge", function (params) {
        if (isAddingEdge) {
            const fromNode = params.from; // Узел, от которого начинается связь
            const toNode = params.to; // Узел, к которому ведёт связь

            // Проверяем, что связь создаётся между разными узлами
            if (fromNode !== toNode) {
                const newEdgeId = edges.length + 1; // Генерируем уникальный ID для связи
                edges.add({
                    id: newEdgeId,
                    from: fromNode,
                    to: toNode,
                    smooth: false
                });

                console.log(`Добавлена связь с ID: ${newEdgeId}`, { from: fromNode, to: toNode });
            } else {
                console.error("Нельзя создать связь между одним и тем же узлом.");
            }

            // Выключаем режим добавления связи после создания
            isAddingEdge = false;
            addEdgeButton.textContent = "Добавить связь";
            network.disableEditMode();
            network.on("click", handleNodeClick); // Включаем обработчик клика на узлы
        }
    });

    // Логика для редактирования и удаления узла
    const editNodeButton = document.getElementById("edit-node-button");
    const deleteNodeButton = document.getElementById("delete-node-button");
    let selectedNodeId = null; // ID выбранного узла

    // Обработчик клика на узлы
    function handleNodeClick(params) {
        if (params.nodes.length > 0) {
            selectedNodeId = params.nodes[0]; // Сохраняем ID выбранного узла
            const node = nodes.get(selectedNodeId);

            // Отображаем информацию о узле в модальном окне
            const nodeInfoContent = document.getElementById("node-info-content");
            nodeInfoContent.innerHTML = `
                <p><strong>ID:</strong> ${node.id}</p>
                <p><strong>Имя:</strong> ${node.label}</p>
                <p><strong>Тип:</strong> ${node.type}</p>
                <p><strong>Описание:</strong> ${node.description}</p>
                <p><strong>Интерфейсы:</strong></p>
                <ul>
                    ${node.interfaces.map(iface => `
                        <li>${iface.name}: ${iface.ip}</li>
                    `).join("")}
                </ul>
            `;

            // Открываем модальное окно
            const nodeInfoModal = document.getElementById("node-info-modal");
            nodeInfoModal.style.display = "block";
        }
    }

    // Обработчик для кнопки "Редактировать"
    editNodeButton.addEventListener("click", function () {
        if (selectedNodeId !== null) {
            const node = nodes.get(selectedNodeId);

            // Открываем модальное окно для редактирования
            const editNodeModal = document.getElementById("add-node-modal");
            const nodeForm = document.getElementById("node-form");

            // Заполняем форму данными узла
            document.getElementById("node-type").value = node.type;
            document.getElementById("node-name").value = node.label;
            document.getElementById("node-description").value = node.description || ""; // Заполняем описание

            // Очищаем контейнер интерфейсов
            const interfacesContainer = document.getElementById("interfaces-container");
            interfacesContainer.innerHTML = "";

            // Добавляем интерфейсы
            node.interfaces.forEach((iface, index) => {
                const newInterface = document.createElement("div");
                newInterface.className = "interface";
                newInterface.innerHTML = `
                    <label>Интерфейс ${index + 1}:</label>
                    <input type="text" placeholder="Имя интерфейса" class="interface-name" value="${iface.name}" required>
                    <input type="text" placeholder="IP-адрес" class="interface-ip" value="${iface.ip}" required>
                `;
                interfacesContainer.appendChild(newInterface);
            });

            // Открываем модальное окно
            editNodeModal.style.display = "block";

            // Закрываем модальное окно с информацией о узле
            const nodeInfoModal = document.getElementById("node-info-modal");
            nodeInfoModal.style.display = "none";
        }
    });

    // Обработчик для кнопки "Удалить"
    deleteNodeButton.addEventListener("click", function () {
        if (selectedNodeId !== null) {
            // Удаляем узел из DataSet
            nodes.remove(selectedNodeId);

            // Удаляем все связи, связанные с этим узлом
            const edgesToRemove = edges.get({
                filter: edge => edge.from === selectedNodeId || edge.to === selectedNodeId
            });
            edges.remove(edgesToRemove.map(edge => edge.id));

            console.log(`Узел с ID ${selectedNodeId} удалён.`);

            // Закрываем модальное окно
            const nodeInfoModal = document.getElementById("node-info-modal");
            nodeInfoModal.style.display = "none";
        }
    });

    // Включаем обработчик клика на узлы по умолчанию
    network.on("click", handleNodeClick);

    // Логика для модального окна информации о узле
    const nodeInfoModal = document.getElementById("node-info-modal");
    const closeNodeInfoModal = nodeInfoModal.querySelector(".close");

    // Закрываем модальное окно информации о узле
    closeNodeInfoModal.addEventListener("click", function () {
        nodeInfoModal.style.display = "none";
    });

    // Закрываем модальное окно при клике вне его
    window.addEventListener("click", function (event) {
        if (event.target === nodeInfoModal) {
            nodeInfoModal.style.display = "none";
        }
        if (event.target === addNodeModal) {
            addNodeModal.style.display = "none";
        }
    });

    // Логика для сохранения топологии
    const saveTopologyButton = document.getElementById("save-topology-button");

    saveTopologyButton.addEventListener("click", function () {
        // Получаем текущее состояние узлов и связей
        const nodesData = nodes.get();
        const edgesData = edges.get();

        // Формируем данные для отправки на сервер
        const topologyData = {
            nodes: nodesData.map(node => ({
                id: node.id,
                label: node.label,
                x: node.x, // Сохраняем координаты X
                y: node.y, // Сохраняем координаты Y
                type: node.type,
                description: node.description,
                interfaces: node.interfaces
            })),
            links: edgesData.map(edge => ({
                id: edge.id, // Сохраняем ID связи
                source: edge.from,
                target: edge.to
            }))
        };

        // Логируем данные перед отправкой
        console.log("Данные для сохранения:", topologyData);

        // Отправляем данные на сервер
        fetch("/save_topology", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(topologyData),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Топология успешно сохранена!");
            } else {
                alert("Ошибка при сохранении топологии: " + data.message);
            }
        })
        .catch(error => {
            console.error("Ошибка при отправке данных:", error);
            alert("Ошибка при сохранении топологии.");
        });
    });
});
