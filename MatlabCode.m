excelFilePath = 'C:\Users\SWA\Downloads\rover_2\Testexcel\data.xlsx';
% Use xlsread to read the Excel file
data = xlsread(excelFilePath);


columnE = data(:, 5);

% Calculate the average of the last 60 values in column D
if length(columnE) >= 60
    last60Values = columnE(end-59:end);
    value = mean(last60Values);
end

Energy_remaining=value;

disp(Energy_remaining)