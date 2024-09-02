# import asyncio

# # 定义一个异步函数
# async def async_function(number):
#     print(number)
#     await asyncio.sleep(1)  # 模拟异步操作
    

# async def main():
#     print("Before running async function")
    
#     tasks=[asyncio.create_task(async_function(i)) for i in range(3)]
#     print(tasks)
#     await asyncio.gather(*tasks)
#     print(tasks)
#     print("After running async function")

# # 运行 main 函数
# if __name__ == "__main__":
#     asyncio.run(main())

# import multiprocessing

# def prt(num):
#     print(num)

# def main(num):
#     pool=multiprocessing.Pool()
#     pool.map(prt,range(num))
#     pool.close()
#     pool.join()

# if __name__=='__main__':
#     pool=multiprocessing.Pool()
#     pool.map(main,range(2,4))
#     pool.close()
#     pool.join()
import time
s=time.time()
time.sleep(2)
e=time.time()
print('tIEM %s',round(e-s,3))