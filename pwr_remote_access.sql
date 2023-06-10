CREATE TABLE `users` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `email` varchar(255),
  `password` varchar(255),
  `name` varchar(255),
  `access_level` int
);

CREATE TABLE `devices` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255),
  `location` varchar(255),
  `power_on` int,
  `is_power_on` int,
  `value` int,
  `safety_level` int
);
