document.addEventListener("DOMContentLoaded", function () {
    // Получаем данные из атрибута data-topology
    const topologyDataElement = document.getElementById("topology-data");
    const rawData = topologyDataElement.getAttribute("data-topology");
    console.log("Raw data from Flask:", rawData);

    // Получаем пути к изображениям из атрибутов
    const nodeImages = {
        server: topologyDataElement.getAttribute("data-server-image"),
        workstation: topologyDataElement.getAttribute("data-workstation-image"),
        switch: topologyDataElement.getAttribute("data-switch-image"),
        router: topologyDataElement.getAttribute("data-router-image"),
        firewall: topologyDataElement.getAttribute("data-firewall-image")
    };

    console.log("Node images:", nodeImages);

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
    const nodes = new vis.DataSet(
        topologyData.nodes.map(node => ({
            id: node.id,
            label: node.domain || node.label,
            name: node.name,
            x: node.x,
            y: node.y,
            description: node.description,
            domain: node.domain,
            type: node.type,
            shape: "image",
            image: nodeImages[node.type] || "https://via.placeholder.com/50/000000/FFFFFF?text=Node", // Fallback
            size: 30
        }))
    );

    const edges = new vis.DataSet(
        topologyData.links.map(link => ({
            id: link.id,
            from: link.source,
            to: link.target,
            smooth: false // Прямые линии
        }))
    );

    // Настройки сети
    const options = {
        physics: false, // Отключаем физику
        edges: {
            smooth: false, // Прямые линии
            arrows: {
                to: { enabled: true, scaleFactor: 0.5 } // Стрелки на концах линий (опционально)
            },
            color: {
                color: "#2B7CE9", // Цвет линий
                highlight: "#2B7CE9",
                hover: "#2B7CE9",
                inherit: false
            },
            width: 2 // Толщина линий
        },
        nodes: {
            borderWidth: 2, // Толщина границы узлов
            color: {
                border: "#2B7CE9", // Цвет границы узлов
                background: "#FFFFFF", // Цвет фона узлов
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
                color: "#000000", // Цвет текста
                size: 14, // Размер текста
                face: "Arial" // Шрифт
            }
        }
    };

    // Создаем сеть
    const data = { nodes: nodes, edges: edges };
    const network = new vis.Network(container, data, options);
});
