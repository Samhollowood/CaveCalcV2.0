#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 19 17:53:33 2024

@author: samhollowood
"""

# Prepare Output Ranges DataFrame
output_ranges_data = {
    'Variable': ['CaveCalc d13C', 'CaveCalc d18O', 'CaveCalc MgCa', 'CaveCalc SrCa', 
                 'CaveCalc BaCa', 'CaveCalc UCa', 'CaveCalc d44Ca', 'CaveCalc DCP'],
    'Minimum': [None] * 8,
    'Maximum': [None] * 8
}

output_ranges_df = pd.DataFrame(output_ranges_data)

# Initialize an empty list to store updated records
all_record = []

# Iterate through the data points
for index in range(len(age_data)):
    # Base dictionary with common keys for CaveCalc X/Ca values
    all_records = {
        'Age': age_data[index],
        'CaveCalc d13C': d13C_spel,
        'CaveCalc d18O': d18O_spel if d18O_data else np.nan,
        'CaveCalc MgCa': MgCa_spel if MgCa_data else np.nan,
        'CaveCalc SrCa': SrCa_spel if SrCa_data else np.nan,
        'CaveCalc BaCa': BaCa_spel if BaCa_data else np.nan,
        'CaveCalc UCa': UCa_spel if UCa_data else np.nan,
        'CaveCalc d44Ca': d44Ca_spel if d44Ca_data else np.nan,
        'CaveCalc DCP': dcp_spel if dcp_data else np.nan
    }

    # Append the record to the list
    all_record.append(all_records)

# Convert the collected records to a DataFrame for further processing
all_record_df = pd.DataFrame(all_record)

# Check if the Excel file exists
if not os.path.exists(excel_file):
    # Create a new Excel file and write the Tolerances, Input Ranges, and Output Ranges sheets
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        tolerance_df.to_excel(writer, sheet_name='Tolerances', index=False)
        input_ranges_df.to_excel(writer, sheet_name='Input Ranges', index=False)
        output_ranges_df.to_excel(writer, sheet_name='Output Ranges', index=False)
        all_record_df.to_excel(writer, sheet_name='All outputs', index=False)
    print(f"Created new file '{excel_file}' and saved Tolerances, Input Ranges, and Output Ranges.")
else:
    with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        # Append data to 'All outputs' sheet
        startrow = writer.sheets['All outputs'].max_row if 'All outputs' in writer.sheets else 0
        all_record_df.to_excel(writer, sheet_name='All outputs', index=False, header=startrow == 0, startrow=startrow)

        # Tolerances sheet handling
        if 'Tolerances' in writer.sheets:
            writer.book.remove(writer.sheets['Tolerances'])  # Remove existing Tolerances sheet
            tolerance_df.to_excel(writer, sheet_name='Tolerances', index=False)  # Write updated data

        # Input Ranges sheet handling
        if 'Input Ranges' in writer.sheets:
            existing_df = pd.read_excel(excel_file, sheet_name='Input Ranges')
            for variable in input_ranges_data['Variable']:
                if variable in existing_df['Variable'].values:
                    existing_df.loc[existing_df['Variable'] == variable, 'Minimum'] = min(
                        existing_df.loc[existing_df['Variable'] == variable, 'Minimum'].dropna().tolist() + [eval(variable)],
                        default=None)
                    existing_df.loc[existing_df['Variable'] == variable, 'Maximum'] = max(
                        existing_df.loc[existing_df['Variable'] == variable, 'Maximum'].dropna().tolist() + [eval(variable)],
                        default=None)
                else:
                    new_row = pd.DataFrame({
                        'Variable': [variable],
                        'Minimum': [eval(variable)],
                        'Maximum': [eval(variable)]
                    })
                    existing_df = pd.concat([existing_df, new_row], ignore_index=True)
            existing_df.to_excel(writer, sheet_name='Input Ranges', index=False)

        # Output Ranges sheet handling (same structure as Input Ranges)
        if 'Output Ranges' in writer.sheets:
            existing_output_df = pd.read_excel(excel_file, sheet_name='Output Ranges')
            for variable in output_ranges_data['Variable']:
                if variable in existing_output_df['Variable'].values:
                    existing_output_df.loc[existing_output_df['Variable'] == variable, 'Minimum'] = min(
                        existing_output_df.loc[existing_output_df['Variable'] == variable, 'Minimum'].dropna().tolist() + [eval(variable)],
                        default=None)
                    existing_output_df.loc[existing_output_df['Variable'] == variable, 'Maximum'] = max(
                        existing_output_df.loc[existing_output_df['Variable'] == variable, 'Maximum'].dropna().tolist() + [eval(variable)],
                        default=None)
                else:
                    new_output_row = pd.DataFrame({
                        'Variable': [variable],
                        'Minimum': [eval(variable)],
                        'Maximum': [eval(variable)]
                    })
                    existing_output_df = pd.concat([existing_output_df, new_output_row], ignore_index=True)
            existing_output_df.to_excel(writer, sheet_name='Output Ranges', index=False)
        else:
            output_ranges_df.to_excel(writer, sheet_name='Output Ranges', index=False)
