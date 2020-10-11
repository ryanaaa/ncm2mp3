import base64
import binascii
from Crypto.Cipher import AES
import click
import os
import os.path as osp
import struct
import json


def ncm2mp3(src_path, des_path):
    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")

    def unpad(s):
        return s[0: -(s[-1] if type(s[-1]) == int else ord(s[-1]))]

    with open(src_path, 'rb') as f:
        header = f.read(8)
        assert binascii.b2a_hex(header) == b'4354454e4644414d'
        f.seek(2, 1)
        key_length = f.read(4)
        key_length = struct.unpack('<I', bytes(key_length))[0]
        key_data = f.read(key_length)
        key_data_array = bytearray(key_data)
        for i in range(0, len(key_data_array)):
            key_data_array[i] ^= 0x64

        key_data = bytes(key_data_array)
        cryptor = AES.new(core_key, AES.MODE_ECB)
        key_data = unpad(cryptor.decrypt(key_data))[17:]
        key_length = len(key_data)
        key_data = bytearray(key_data)
        key_box = bytearray(range(256))
        c = 0
        last_byte = 0
        key_offset = 0
        for i in range(256):
            swap = key_box[i]
            c = (swap + last_byte + key_data[key_offset]) & 0xff
            key_offset += 1
            if key_offset >= key_length:
                key_offset = 0
            key_box[i] = key_box[c]
            key_box[c] = swap
            last_byte = c
        meta_length = f.read(4)
        meta_length = struct.unpack('<I', bytes(meta_length))[0]
        meta_data = f.read(meta_length)
        meta_data_array = bytearray(meta_data)
        for i in range(0, len(meta_data_array)):
            meta_data_array[i] ^= 0x63
        meta_data = bytes(meta_data_array)
        meta_data = base64.b64decode(meta_data[22:])
        cryptor = AES.new(meta_key, AES.MODE_ECB)
        meta_data = unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:]
        meta_data = json.loads(meta_data)
        crc32 = f.read(4)
        crc32 = struct.unpack('<I', bytes(crc32))[0]
        f.seek(5, 1)

        image_size = f.read(4)
        image_size = struct.unpack('<I', bytes(image_size))[0]
        image_data = f.read(image_size)
        file_name = meta_data['musicName'] + '.' + meta_data['format']

        with open(des_path, "wb") as m:
            chunk = bytearray()
            while True:
                chunk = bytearray(f.read(0x8000))
                chunk_length = len(chunk)
                if not chunk:
                    break
                for i in range(1, chunk_length + 1):
                    j = i & 0xff
                    chunk[i-1] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
                m.write(chunk)


@click.command()
@click.help_option("-h", "--help")
@click.option("-s", "--src", "src_dir", type=str, required=True)
@click.option("-d", "--des", "des_dir", type=str, default=None)
def convert_music(src_dir, des_dir):
    if des_dir is None:
        des_dir = osp.abspath(src_dir) + ".Convert"

    print("src_dir = {}".format(src_dir))
    print("des_dir = {}".format(des_dir))

    if not osp.exists(des_dir):
        os.makedirs(des_dir)

    fn_list = sorted([f for f in os.listdir(src_dir)])
    for _i, fn in enumerate(fn_list):
        src_path = osp.join(src_dir, fn)
        des_path = osp.join(des_dir, osp.splitext(fn)[0] + ".mp3")

        if osp.exists(des_path):
            print("[{}/{}] Skip converted : {}".format(_i + 1, len(fn_list), des_path))
            continue

        if src_path.endswith(".mp3") or src_path.endswith(".flac"):
            print("[{}/{}] Copy {} -> {}".format(_i + 1, len(fn_list), src_path, des_path))
            os.system('cp "{}" "{}"'.format(src_path, des_path))
            continue

        assert src_path.endswith(".ncm"), \
            "[{}/{}] Find no-ncm file : {}".format(_i + 1, len(fn_list), src_path)

        print("[{}/{}] Convert {} -> {}".format(_i + 1, len(fn_list), src_path, des_path))
        ncm2mp3(src_path, des_path)


if __name__ == '__main__':
    convert_music()
