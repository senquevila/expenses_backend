function save_form_data() {
    const formData = {
        start_row: $("#id_start_row").val(),
        end_row: $("#id_end_row").val(),
        payment_date: $("#id_payment_date").val(),
        description: $("#id_description").val(),
        amount_debit: $("#id_amount_debit").val(),
        amount_credit: $("#id_amount_credit").val(),
        currency: $("#id_currency").val(),
    };
    localStorage.setItem("expenseFormData", JSON.stringify(formData));
}

function load_form_data() {
    const formData = JSON.parse(localStorage.getItem("expenseFormData"));
    if (formData) {
        $("#id_start_row").val(formData.start_row);
        $("#id_end_row").val(formData.end_row);
        $("#id_payment_date").val(formData.payment_date);
        $("#id_description").val(formData.description);
        $("#id_amount_debit").val(formData.amount_debit);
        $("#id_amount_credit").val(formData.amount_credit);
    }
}

function run(data) {
    initialize_page(data, load_form_data, save_form_data, normalize_data);
}

export { run };