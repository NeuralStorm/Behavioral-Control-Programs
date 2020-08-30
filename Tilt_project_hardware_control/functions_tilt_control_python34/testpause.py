import time
x=1
while True:
    try:
        
        time.sleep(1)  # code goes here
        print(x)
        x+=1

    except KeyboardInterrupt:
        print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
        try:
            response = input()
            if response == 'quit':
                break
            print('Resuming...')
        except KeyboardInterrupt:
            print('Resuming...')
            continue
