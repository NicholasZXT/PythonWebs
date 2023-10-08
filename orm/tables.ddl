CREATE TABLE `user_v1` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(64) DEFAULT NULL,
  `gender` varchar(64) DEFAULT NULL,
  `age` int DEFAULT NULL,
  `province` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='User table';

CREATE TABLE `user_v2` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(64) DEFAULT NULL,
  `gender` varchar(64) DEFAULT NULL,
  `age` int DEFAULT NULL,
  `province` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

REPLACE INTO `user_v1` (id, name, gender, age, province) VALUES ('1', 'daniel', 'male', 26, 'anhui');
REPLACE INTO `user_v1` (id, name, gender, age, province) VALUES ('2', 'jane', 'female', 23, 'anhui');
REPLACE INTO `user_v1` (id, name, gender, age, province) VALUES ('3', 'wendy', 'female', 27, 'zhejiang');
REPLACE INTO `user_v1` (id, name, gender, age, province) VALUES ('4', 'jack', 'male', 21, 'zhejiang');

REPLACE INTO `user_v2` (id, name, gender, age, province) VALUES ('1', 'daniel', 'male', 26, 'anhui');
REPLACE INTO `user_v2` (id, name, gender, age, province) VALUES ('2', 'jane', 'female', 23, 'anhui');
REPLACE INTO `user_v2` (id, name, gender, age, province) VALUES ('3', 'wendy', 'female', 27, 'zhejiang');
REPLACE INTO `user_v2` (id, name, gender, age, province) VALUES ('4', 'jack', 'male', 21, 'zhejiang');