# Changelog
## 2025-12-15
### New
- Add DEFAULT_EXPENSE_ACCOUNT and DEFAULT_INCOME_ACCOUNT in the settings.
### Change
- Update the upload process to identify start and end dates from the entire file.
- Fix flake8 configurations.
## 2025-05-04
### New
- Add INVALID_ACCOUNT in the settings.
## 2025-04-17
### New
- Install black, isort, and flake8 for code formatting and linting.
- Add start_date and end_date to the period model.
## 2025-03-23
### New
- Add action to inactive all the completed loans.
## 2025-02-23
### Change
- Update the upload process to include a multiple choice of currencies for the account type.
## 2025-01-05
### Change
- Divide the upload process into steps to determine whether the file pertains to credit card or bank account transactions.
## 2025-01-01
### Change
- Use local storage for number of rows in the upload process.
## 2024-10-20
### New
- Add search by upload file in transaction admin.
- Loan and Subscription views to list and create items.
### Change
- Fallback for invalid dates in the upload process.
- Use absolute values for the uploaded amounts.
## 2024-10-03
### New
- Set the currency conversion day range to 90 days.
### Change
- Fix the local amount calculation.
- Correct the current conversion endpoint.
- Ensure the amounts are absolute values.
- Skip any invalid rows during the upload process.
## 2024-09-04
### Change
- Fix the currency in the programmed tasks.
## 2024-08-11
### Change
- New way to get the difference between the budget and the expenses.
- Fix the get the currency exchange.
## 2024-08-07
### New
- Add Subscription model and admin.
## 2024-08-04
### New
- Save the upload configuration into local storage.
- Add commands to the page view.
- Add Loan model and admin.
## 2024-07-14
### New
- Add a form to create a period.
### Change
- Configure signals in the project.
- Fix pagination while maintaining the query parameters.
- Ensure a period has a unique year and month.

## 2024-06-10
### New
- Add an identifier to check unique transactions.
### Change
- Simplify the inspection process.

## 2024-06-09
### New
- Add testing.
- Add programmed transactions.
### Change
- Fix currency extraction.

## 2024-05-20
### Change
- Validate the transformation when the index is not valid (-1).
- Divide the processing of amounts (local or foreign).

## 2024-05-12
### New
- [Admin] Update period administration.
### Change
- Fix the issue when the amount is empty in the upload file.
### Remove
- Remove the result view from the upload process view. The result can be seen in the period actions.

## 2024-04-28
- Change the upload process by adding preliminary steps to process a raw CSV.

## 2024-03-18
### New
- Edit accounts from recent uploads directly.
- Add `get_local_amount` in admin actions.

## 2024-03-02
### New
- Add translations on model fields and `verbose_name`.

### Change
- Update the process to extract the amount and currency in expense uploads.
- Rename the expense model to transaction.

## 2024-02-18
### New
- Add `account_type` to the account model.
- Add a changelog template with New, Fixed, and Removed subtitles.

### Change
- Implement cascade delete on foreign key fields.
- Update the upload result template.
- Update budget assignments.

### Remove
- Remove the swap account view.
- Remove Category and MatchAccount models.

## 2024-02-04
### New
- Enable period activations.
- Add admin form actions: remove blank uploads, remove invalid expenses, disable periods.

### Change
- Update the upload expense result to give details for all rows.

## 2024-01-28
### New
- Add Redux URLs.
- Update expenses in the budget.
- List expense categories associated with the budget.
- Display results from expense uploads.

### Change
- Cleanup the database when an upload does not have associated expenses.

## 2024-01-21
- Create expenses CRUD forms.
- Implement the upload model.
- Show results from uploading an expense file.

## 2024-01-14
### New
- Add the budget app.
- Translate account fields.

## 2024-01-13
### New
- Automate account association by searching for reserved tokens in expense descriptions.

## 2024-01-04
### New
- Add the open periods endpoint.
- Link to use CDN font from Bootstrap.

### Change
- Update the changelog format to use the verbs: Added, Changed, and Removed.

## 2024-01-01
### New
- Add Bank and BankAccount models.

### Remove
- Remove unused API endpoints.

## 2023-12-31
### Change
- Update the filter to omit closed periods in the expenses uploads.

### Remove
- Remove the period from upload expenses. This field will be calculated from the payment date.

## 2023-11-04
### New
- Add `local_amount` field to the Expense model.
- Add `populate_local_amount` command.
- Add `refresh_period_total` command.
- Implement USD conversion when uploading expenses.

## 2023-10-15
### New
- Create a conversion object when it is created.
- Add a script to call the conversion endpoint.

## 2023-10-03
### New
- Add account list.
- Add currency convert list.
- Create home.html.

## 2023-09-24
### New
- Add the ability to close a period.
- Create HTML templates for listing periods and expenses.
- Create HTML templates for uploading expense CSV files.
