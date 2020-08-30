    def FormatDurations(self, filename, fullfilename, Ranges):
        for key, values in Ranges.items():
            self.csvdict['EndRanges' + str(key)] = values
        csvtest = True
        while csvtest == True:
            try:
                check = os.path.isfile(fullfilename)
                while check == True:
                    print('File name already exists')
                    filename = input('Enter File name: ')
                    fullfilename = filename + '.csv'
                    check = os.path.isfile(fullfilename)
                print('File name not currently used, saving.')

                with open(filename + '.csv', 'w', newline = '') as csvfile:
                    csv_writer = writer(csvfile, delimiter = ',')
                    for key in self.csvdict.keys():
                        csv_writer.writerow([key]+self.csvdict[key])
                csvtest = False
                # with open(name + '.csv', newline = '') as csv_read, open(data +'.csv', 'w', newline = '') as csv_write:
                #     writer(csv_write, delimiter= ',').writerows(zip(*reader(csv_read, delimiter=',')))
            except:
                print('Error with File name')
        print(fullfilename)