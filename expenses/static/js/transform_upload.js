const columns = [
    {
        id: "id_payment_date",
        color: "#7FFFD4", // Aquamarine
    },
    {
        id: "id_description",
        color: "#E9967A", // Dark Salmon
    },
    {
        id: "id_amount_debit",
        color: "#F0E68C", // Khaki
    },
    {
        id: "id_amount_credit",
        color: "#7B68EE", // Medium Slate Blue
    },
    {
        id: "id_amount",
        color: "#F0E68C", // Khaki
    },
    {
        id: "id_amount_currency",
        color: "#7B68EE", // Medium Slate Blue
    },
];

const rangeInputs = ["#id_start_row", "#id_end_row"];

function get_range_object(data) {
    const storedEndRow = localStorage.getItem("expenseFormData");
    const a = data.length - 1;
    const b = storedEndRow ? parseInt(storedEndRow, 10) : 0;

    const maxLength = data.reduce((max, item) => {
        const length = Object.keys(item).length;
        return length > max ? length : max;
    }, 0);

    return {
        num_row: Math.max(a, b),
        num_col: maxLength,  // Include the line number column
    };
}

function set_input_range(num_row, num_col) {
    const min_col = -1;
    const max_col = num_col - 1;
    const min_row = 0;
    const max_row = num_row - 2;

    columns.forEach(function (column) {
        $("#" + column.id).attr({
            min: min_col,
            max: max_col,
        });
    });

    rangeInputs.forEach(function (id) {
        $(id).attr({
            min: min_row,
            max: max_row,
        });
    });
}

function get_all_keys(data) {
    let allKeys = new Set();
    data.forEach((item) => {
        Object.keys(item).forEach((key) => allKeys.add(key));
    });
    return Array.from(allKeys);
}

function normalize_data(data, keys) {
    return data.map((item) => {
        let normalized = {};
        keys.forEach((key) => {
            normalized[key] = item.hasOwnProperty(key) ? item[key] : ""; // Or `null` or some other default
        });
        return normalized;
    });
}

function change_color_bullet() {
    columns.forEach((column) => {
        $("#color-" + column.id).css("background-color", column.color);
    });
}

function get_index(id) {
    return parseInt($("#" + id).val());
}

function repaint_row() {
    const startRow = parseInt($(rangeInputs[0]).val(), 10);
    const endRow = parseInt($(rangeInputs[1]).val(), 10);
    const rows = $("#example tbody tr");

    rows.each(function () {
        const cells = $(this).find("td");
        // Get the value of the first column of the current row, assuming it's an integer
        const rowValue = parseInt(cells.eq(0).text(), 10);

        // Check if the value of the first column is outside the specified range
        if (rowValue < startRow || rowValue > endRow) {
            cells.each(function () {
                const bgColor = $(this).css("background-color");
                $(this).css("color", bgColor); // Set the text color to match the background color
            });
        } else {
            cells.each(function () {
                $(this).css("color", ""); // Reset text color to default
            });
        }
    });
}

function repaint_column() {
    $("#example tbody tr").each(function () {
        // Reset all cells to white initially to clear previous colors
        $(this).find("td").css("background-color", "white");

        // Apply specific colors from the columns configuration
        $(this)
            .find("td")
            .each(function (cellIndex) {
                columns.forEach((column) => {
                    if (cellIndex === get_index(column.id)) {
                        $(this).css("background-color", column.color);
                    }
                });
            });
    });

    repaint_row();
}

function initialize_page(data, load_form_data, save_form_data, normalize_data, dimension) {
    load_form_data();

    if (data.length > 0) {
        const allKeys = get_all_keys(data);
        const normalizedData = normalize_data(data, allKeys);

        var columns = allKeys.map(function (key) {
            return {
                title: key.charAt(0).toUpperCase() + key.slice(1),
                data: key,
                defaultContent: "",
            };
        });

        var TheDataTable = $("#example").DataTable({
            data: normalizedData,
            columns: columns,
        });

        TheDataTable.on("draw", function () {
            repaint_column();
        });
    }

    const rawRange = get_range_object(data);
    const num_row = isNaN(rawRange.num_row) ? dimension.rows : rawRange.num_row;
    const num_col = isNaN(rawRange.num_col) ? dimension.cols : rawRange.num_col;

    $(".repaint-col-trigger").on("change", function () {
        console.log("Repainting columns...");
        repaint_column();
    });

    $(".repaint-row-trigger").on("change", function () {
        console.log("Repainting rows...");
        repaint_row();
    });

    $("#expenseForm").on("submit", function (e) {
        e.preventDefault();
        save_form_data();
        this.submit();
    });

    change_color_bullet();
    set_input_range(num_row, num_col);
    repaint_column();
}