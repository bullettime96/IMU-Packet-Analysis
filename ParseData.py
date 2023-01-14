import struct
import argparse
import csv

BUFFER_SIZE = 255
PACKET_START_BYTE = b'\xcc'
ACCELEROMETER_START_BYTE = b'\xea'
GYRO_START_BYTE = b'\xeb'

packetsRead = []

parser = argparse.ArgumentParser(description= 'Parser script for IMU data.')

parser.add_argument('InFile', type=str, help='A required input file with binary data from sensors')
parser.add_argument('-o', type=str, help='Output file for parsed data in CSV format (semicolon delimiter).')
parser.add_argument('--debug', required=False, default=False, action='store_true', help='Enable debug mode.')

args = parser.parse_args()

DEBUG_MODE = args.debug

print(csv.list_dialects())

if DEBUG_MODE:
    if not args.o:
        print('Output file not specified. The parsed data will be output to console only.')

def parsePacket(rawPacket):
    if DEBUG_MODE:
        print('Packet parser called.')
    outPacket = \
        {
            'length': len(rawPacket)
        }
    if DEBUG_MODE:
        print('Packet length: ', outPacket['length'])
    if outPacket['length'] <= 6:
        print('Invalid packet length')
        return None

    timestamp = b''
    for i in range(2,6):
        timestamp += rawPacket[i: i + 1]
    try:
        outPacket['timestamp'] = int.from_bytes(timestamp, 'big', signed=False)
    except struct.error as exc:
        print('Error occurred during timestamp conversion.')
        print(str(exc))
        return None
    if DEBUG_MODE:
        print('Packet timestamp: ', outPacket['timestamp'])

    outPacket['accData'] = []
    accelerometerReading = False
    accelerometerBytesRead = 0

    outPacket['gyroData'] = []
    gyroscopeReading = False
    gyroscopeBytesRead = 0

    try:
        for i in range(6, outPacket['length']):
            if accelerometerReading:
                outPacket['accData'][-1] += rawPacket[i: i + 1]
                accelerometerBytesRead += 1
                if accelerometerBytesRead == 12:
                    if DEBUG_MODE:
                        print('Got 12 bytes for acceleration. Raw data: ', outPacket['accData'][-1])

                    DataParsed = list(struct.unpack('3f', outPacket['accData'][-1]))
                    outPacket['accData'][-1] = DataParsed

                    if DEBUG_MODE:
                        print('Parsed values: ', DataParsed)
                    accelerometerReading = False
                    continue
            if gyroscopeReading:
                outPacket['gyroData'][-1] += rawPacket[i: i + 1]
                gyroscopeBytesRead += 1
                if gyroscopeBytesRead == 12:
                    if DEBUG_MODE:
                        print('Got 12 bytes for gyroscope. Raw data: ', outPacket['gyroData'][-1])

                    DataParsed = list(struct.unpack('3f', outPacket['gyroData'][-1]))
                    outPacket['gyroData'][-1] = DataParsed

                    if DEBUG_MODE:
                        print('Parsed values: ', DataParsed)
                    gyroscopeReading = False
                    continue
            if rawPacket[i: i + 1] == ACCELEROMETER_START_BYTE:
                if DEBUG_MODE:
                    print('Found accelerometer data. Reading...')
                accelerometerReading = True
                accelerometerBytesRead = 0
                outPacket['accData'].append(b'')
            if rawPacket[i: i + 1] == GYRO_START_BYTE:
                if DEBUG_MODE:
                    print('Found gyroscope data. Reading...')
                gyroscopeReading = True
                gyroscopeBytesRead = 0
                outPacket['gyroData'].append(b'')
    except struct.error as exc:
        print('Error occurred during packet data parsing')
        print(str(exc))
        return None

    return outPacket


try:
    with open( args.InFile, 'rb') as file:
        packetProcessing = False
        packet = b''
        packetLength = 0
        while True:
            char = file.read(1)
            if not char:
                break

            if char == PACKET_START_BYTE and not packetProcessing:
                print('Found start byte')
                packetProcessing = True
                packet += char
                continue

            if packetProcessing:
                packet += char
                if len(packet) == 2:
                    packetLength = ord(char)
                    print('Packet length: ', packetLength)
                else:
                    if len(packet) == packetLength:
                        parsedPacket = parsePacket(packet)
                        if not parsedPacket:
                            print('Invalid packet.')
                        else:
                            packetsRead.append(parsedPacket)
                            print('Packet parsed.')
                        packetProcessing = False
                        packetLength = 0
                        packet = b''
except FileNotFoundError as exc:
    print('Data file ', args.InFile, ' not found.')
if DEBUG_MODE:
    print('Parsing finished. Packets parsed: ', len(packetsRead))

if args.o:
    if len(args.o) <= 4:
        print('Output filename too short. Minimal length is 4 characters.')

    headers = ['timestamp', 'accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ']

    outFile = args.o
    if outFile[-4:] != '.csv':
        outFile += '.csv'

    if DEBUG_MODE:
        print('Writing data to output file.')
    with open(outFile, 'w') as file:
        dialect = csv.unix_dialect
        dialect.delimiter = ';'
        dialect.quoting = csv.QUOTE_MINIMAL
        writer = csv.DictWriter(file, fieldnames=headers, dialect=dialect)
        writer.writeheader()
        for packet in packetsRead:
            if DEBUG_MODE:
                print('Writing packet: ', packet)
            writer.writerow({
                'timestamp': packet['timestamp'],
                'accX': packet['accData'][0][0],
                'accY': packet['accData'][0][1],
                'accZ': packet['accData'][0][2],
                'gyroX': packet['gyroData'][0][0],
                'gyroY': packet['gyroData'][0][1],
                'gyroZ': packet['gyroData'][0][2],
            })
        if DEBUG_MODE:
            print('All data written.')
