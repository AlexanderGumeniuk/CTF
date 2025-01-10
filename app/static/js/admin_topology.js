document.addEventListener("DOMContentLoaded", function () {
    // Получаем данные из атрибута data-topology
    const topologyDataElement = document.getElementById("topology-data");
    const rawData = topologyDataElement.getAttribute("data-topology");

    let topologyData;
    try {
        // Парсим JSON-строку в объект JavaScript
        topologyData = JSON.parse(rawData);
        console.log("Parsed data:", topologyData);
    } catch (error) {
        console.error("Error parsing JSON:", error);
        alert("Ошибка при загрузке данных топологии. Проверьте формат данных.");
        return;
    }

    // Проверка данных
    if (!topologyData || typeof topologyData !== "object") {
        console.error("Некорректные данные топологии: данные не являются объектом", topologyData);
        alert("Некорректные данные топологии: данные не являются объектом.");
        return;
    }

    // Проверка, что nodes — это массив
    if (!Array.isArray(topologyData.nodes)) {
        console.error("Некорректные данные узлов: nodes не является массивом", topologyData.nodes);
        alert("Некорректные данные узлов: nodes не является массивом.");
        return;
    }

    // Проверка, что links — это массив
    if (!Array.isArray(topologyData.links)) {
        console.error("Некорректные данные связей: links не является массивом", topologyData.links);
        alert("Некорректные данные связей: links не является массивом.");
        return;
    }

    // Инициализация узлов
    const nodes = new vis.DataSet(
        topologyData.nodes.map(node => {
            return {
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
        })
    );

    // Инициализация связей
    const edges = new vis.DataSet(
        topologyData.links.map(link => {
            return {
                id: link.id || `${link.source}-${link.target}`, // Генерируем ID, если его нет
                from: link.source,
                to: link.target,
                smooth: false
            };
        })
    );

    // Инициализация контейнера
    const container = document.getElementById("topology-container");
    if (!container) {
        console.error("Контейнер для топологии не найден!");
        return;
    }

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

    // Остальная логика (добавление узлов, связей, редактирование и т.д.)
});
