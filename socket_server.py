import os
import socket
from datetime import datetime


class SocketServer:
    def __init__(self):
        self.bufsize = 1024  # 버퍼 크기 설정
        with open('./response.bin', 'rb') as file:
            self.RESPONSE = file.read()  # 응답 파일 읽기

        self.DIR_PATH = './request'
        self.createDir(self.DIR_PATH)

    def createDir(self, path):
        """디렉토리 생성"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print("Error: Failed to create the directory.")

    def extract_image(self, request):
        """multipart/form-data 요청에서 name="image" 파트의 이진 데이터를 추출"""
        boundary = None
        for line in request.split(b'\r\n'):
            low = line.lower()
            if low.startswith(b'content-type:') and b'multipart/form-data' in low \
                    and b'boundary=' in low:
                boundary = line.split(b'boundary=')[-1].strip().split(b';')[0]
                break
        if boundary is None:
            return None

        body_start = request.find(b'\r\n\r\n')
        if body_start < 0:
            return None
        body = request[body_start + 4:]

        # 각 파트를 boundary로 분리하여 이미지 파트 찾기
        for part in body.split(b'--' + boundary):
            part = part.strip(b'\r\n')
            if not part or part == b'--':
                continue
            header_end = part.find(b'\r\n\r\n')
            if header_end < 0:
                continue
            headers = part[:header_end].lower()
            data = part[header_end + 4:]
            if data.endswith(b'\r\n'):
                data = data[:-2]
            if b'name="image"' in headers and b'image/' in headers:
                return data
        return None

    def run(self, ip, port):
        """서버 실행"""
        # 소켓 생성
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(10)
        print("Start the socket server...")
        print("\"Ctrl+C\" for stopping the server!\r\n")

        try:
            while True:
                # 클라이언트의 요청 대기
                clnt_sock, req_addr = self.sock.accept()
                clnt_sock.settimeout(5.0)  # 타임아웃 설정 (5초)
                print("Request message...\r\n")

                response = b""
                # ------ 구현 ------
                # 요청 전체 수신 (Content-Length 도달 시 완료)
                try:
                    while True:
                        chunk = clnt_sock.recv(self.bufsize)
                        if not chunk:
                            break
                        response += chunk
                        hdr_end = response.find(b'\r\n\r\n')
                        if hdr_end >= 0:
                            clen = None
                            for line in response[:hdr_end].split(b'\r\n'):
                                if line.lower().startswith(b'content-length:'):
                                    clen = int(line.split(b':')[-1].strip())
                                    break
                            if clen is not None and \
                                    len(response) - (hdr_end + 4) >= clen:
                                break  # 본문 전체 수신
                except socket.timeout:
                    pass

                # 실습 1: 요청 원본을 "년-월-일-시-분-초.bin" 이진파일로 저장
                fname = datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '.bin'
                fpath = os.path.join(self.DIR_PATH, fname)
                with open(fpath, 'wb') as f:
                    f.write(response)
                print("Saved request -> %s (%d bytes)" % (fpath, len(response)))

                # 실습 2: 멀티파트 이미지 데이터를 이미지 파일로 저장 후 확인
                image = self.extract_image(response)
                if image is not None:
                    img_path = os.path.join(self.DIR_PATH,
                                            fname[:-4] + '.jpg')
                    with open(img_path, 'wb') as f:
                        f.write(image)
                    print("Saved image  -> %s (%d bytes), head=%r"
                          % (img_path, len(image), image[:4]))
                else:
                    print("No multipart image part found.")
                # ------ 구현 끝 ------

                # 응답 전송
                clnt_sock.sendall(self.RESPONSE)

                # 클라이언트 소켓 닫기
                clnt_sock.close()
        except KeyboardInterrupt:
            print("\r\nStop the server...")

        # 서버 소켓 닫기
        self.sock.close()


if __name__ == "__main__":
    server = SocketServer()
    server.run("127.0.0.1", 8000)
