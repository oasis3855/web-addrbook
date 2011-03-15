#!/usr/bin/perl

use strict;
use warnings;
use utf8;

# ユーザディレクトリ下のCPANモジュールを読み込む
use lib '/home/tmg1136-inue/local/lib/perl5';
use lib '/home/tmg1136-inue/local/lib/perl5/site_perl/5.8.9/mach';

use CGI;
use File::Basename;
use File::Copy;
use DBI; 
use Text::CSV_XS;
use Data::Dumper;
use Encode::Guess qw/euc-jp shiftjis iso-2022-jp/;	# 必要ないエンコードは削除すること

use DBD::SQLite;	# SQLiteバージョンを出すためのみに使用

require '/home/tmg1136-inue/auth/script/auth_md5_utf8.pl';	# 認証システム


my $flag_os = 'linux';	# linux/windows
my $flag_charcode = 'utf8';		# utf8/shiftjis
# IOの文字コードを規定
if($flag_charcode eq 'utf8'){
	binmode(STDIN, ":utf8");
	binmode(STDOUT, ":utf8");
	binmode(STDERR, ":utf8");
}
if($flag_charcode eq 'shiftjis'){
	binmode(STDIN, "encoding(sjis)");
	binmode(STDOUT, "encoding(sjis)");
	binmode(STDERR, "encoding(sjis)");
}


my $str_dir_db = './data';	# DBや一時ファイルが存在するdir名
my $str_filepath_db = $str_dir_db.'/data.sqlite';	# SQLite DBファイル名
my $str_filepath_datastruct = './datastruct.csv';
my $str_filepath_datastruct_tb = './datastruct_thunderbird.csv';
my $str_filepath_datastruct_gm = './datastruct_gmail.csv';
my $str_filepath_csv_tmp = $str_dir_db.'/temp.csv';	# アップロード時の一時ファイル名
my $str_dir_backup = './backup';		# 末尾に / は付けないdir名


my $str_this_script = basename($0);

my $q = new CGI;

# 必要なディレクトリ、ファイルが存在するかチェックする
sub_check_files(\$q);

# ファイルダウンロード処理の場合
if(defined($q->url_param('mode'))){
	if(sub_check_auth($str_this_script, 'web-addrbook', 1) != 1){
		print($q->header(-type=>'text/html', -charset=>'utf-8'));
		print($q->start_html(-dtd=>['-//W3C//DTD XHTML 1.0 Transitional//EN','http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'], -lang=>'ja-JP'));
		print("<p>Not Loggedon</p>\n");
		print($q->end_html);
		exit;
	}
	if($q->url_param('mode') eq 'download_thunderbird'){
		sub_download_csv(\$q, 'thunderbird', 'download');
		exit;
	}
	if($q->url_param('mode') eq 'download_gmail'){
		sub_download_csv(\$q, 'gmail', 'download');
		exit;
	}
}

# 認証状態のチェック（認証されていない場合は、認証画面を表示する）
sub_check_auth($str_this_script, 'web-addrbook', 0);
# ログオフの場合
if(defined($q->url_param('mode')) && $q->url_param('mode') eq 'logoff'){
		sub_logoff_auth($str_this_script, 1);
}

# HTML出力を開始する
sub_print_start_html(\$q);


# 処理内容に合わせた処理と、画面表示
if(defined($q->url_param('mode'))){
	if($q->url_param('mode') eq 'list'){
		sub_list_db();
	}
	if($q->url_param('mode') eq 'backup'){
		sub_backup_db(\$q);
	}
	elsif($q->url_param('mode') eq 'upload_pick'){
		sub_disp_upload_filepick();
	}
	elsif($q->url_param('mode') eq 'download'){
		sub_disp_download();
	}
	elsif($q->url_param('mode') eq 'restore_pick'){
		sub_disp_restore_select();
	}
	elsif($q->url_param('mode') eq 'restore'){
		sub_restore($q->url_param('file'));
	}
}
elsif(defined($q->param('uploadfile')) && length($q->param('uploadfile'))>0){
	my $flag_purge_data = 0;
	if(defined($q->param('purge_data')) && $q->param('purge_data') eq 'purge'){
		$flag_purge_data = 1;
	}
	sub_upload_csv(\$q, $flag_purge_data);
}
else{
	sub_disp_home();
}

# HTML出力を閉じる（フッタ部分の表示）
sub_print_close_html();

exit;


# htmlを開始する（HTML構文を開始して、ヘッダを表示する）
sub sub_print_start_html{

	my $q_ref = shift;	# CGIオブジェクト

	print $$q_ref->header(-type=>'text/html', -charset=>'utf-8');
	print $$q_ref->start_html(-title=>"Thunderbirdアドレス帳CSVの取り込み", -dtd=>['-//W3C//DTD XHTML 1.0 Transitional//EN','http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'], -lang=>'ja-JP', -style=>{'src'=>'style.css'});

# ヘッダの表示
print << '_EOT';
<div style="height:100px; width:100%; padding:0px; margin:0px;"> 
<p><span style="margin:0px 20px; font-size:30px; font-weight:lighter;">Web-Addrbook</span><span style="margin:0px 0px; font-size:25px; font-weight:lighter; color:lightgray;">Thunderbird addressbook web backup</span></p> 
</div> 
_EOT

	# 左ペイン（メニュー）の表示
	print("<div id=\"main_content_left\">\n". 
		"<h2>System</h2>\n");
	{
		my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
		printf("<p>%04d/%02d/%02d %02d:%02d:%02d</p>\n", $year+1900, $mon+1, $mday, $hour, $min, $sec); 
	}
	print("<p>DBD::SQLite ".$DBD::SQLite::sqlite_version."</p>\n");
	print("<h2>Menu</h2>\n".
		"<ul>\n".
		"<li><a href=\"".$str_this_script."\">Home</a></li>\n".
		"<li><a href=\"".$str_this_script."?mode=list\">List Database</a></li>\n".
		"<li><a href=\"".$str_this_script."?mode=backup\">Backup Database</a></li>\n".
		"<li><a href=\"".$str_this_script."?mode=upload_pick\">Upload CSV</a></li>\n".
		"<li><a href=\"".$str_this_script."?mode=download\">Download CSV</a></li>\n".
		"<li><a href=\"".$str_this_script."?mode=restore_pick\">Restore Menu</a></li>\n".
		"<li><a href=\"".$str_this_script."?mode=logoff\">Logoff</a></li>\n".
		"</ul>\n".
		"</div>	<!-- id=\"main_content_left\" -->\n");

	# 右ペイン（主要表示部分）の表示
	print("<div id=\"main_content_right\">\n");

}


# htmlを閉じる（フッタ部分を表示して、HTML構文を閉じる）
sub sub_print_close_html{

print << '_EOT_FOOTER';
<p>&nbsp;</p>
</div>	<!-- id="main_content_right" --> 
<p>&nbsp;</p> 
<div class="clear"></div> 
<div id="footer"> 
<p><a href="http://sourceforge.jp/projects/websvn-admin/">Web-Addrbook</a> version 0.1 &nbsp;&nbsp; GNU GPL free software</p> 
</div>	<!-- id="footer" --> 
_EOT_FOOTER

	print $q->end_html;
}

# エラー終了時に呼ばれるsub
sub sub_error_exit{
	my $str = shift;
	
	print("<p class=\"error\">".(defined($str)?$str:'')."</p>\n");
	sub_print_close_html();
	exit;
}

# エラー終了時に呼ばれるsub （HTML構文が始まっていない場合の入り口）
sub sub_error_exit_with_htmlstart{
	my $q_ref = shift;
	my $str = shift;
	sub_print_start_html($q_ref);
	sub_error_exit($str);
}

# 各種ファイル、DBが読み書きできるか初期チェック（新規作成含む）
sub sub_check_files{
	my $q_ref = shift;
	
	# 必要なディレクトリが存在しなければ作成する
	unless( -d $str_dir_db ){
		mkdir($str_dir_db) or sub_error_exit_with_htmlstart($q_ref, "Error : unable to create ".$str_dir_db);
	}
	unless( -d $str_dir_backup ){
		mkdir($str_dir_backup) or sub_error_exit_with_htmlstart($q_ref, "Error : unable to create ".$str_dir_backup);
	}
	
	# ディレクトリのアクセス権限がなければエラー
	unless( -w $str_dir_db ){ sub_error_exit_with_htmlstart($q_ref, "Error : unable to write at ".$str_dir_db); }
	unless( -w $str_dir_backup ){ sub_error_exit_with_htmlstart($q_ref, "Error : unable to write at ".$str_dir_backup); }

	# DBが存在しなければ、作成する
	sub_make_new_table($q_ref);

	# 定義ファイルを確認する
	unless( -f $str_filepath_datastruct ){ sub_error_exit_with_htmlstart($q_ref, "Error : ".$str_filepath_datastruct." not exist"); }
	unless( -f $str_filepath_datastruct_tb ){ sub_error_exit_with_htmlstart($q_ref, "Error : ".$str_filepath_datastruct_tb." not exist"); }
	unless( -f $str_filepath_datastruct_gm ){ sub_error_exit_with_htmlstart($q_ref, "Error : ".$str_filepath_datastruct_gm." not exist"); }

	# 一時ファイルを消去する
	if( -e $str_filepath_csv_tmp){
		unlink($str_filepath_csv_tmp) or sub_error_exit_with_htmlstart($q_ref, "Error : ".$str_filepath_csv_tmp." not possible delete");
	}

}

sub sub_disp_home{
	print("<h1>Home Screen (ホーム画面)</h1>\n".
		"<p>Databaseに登録されているデータ数を検索中 ...</p>\n");
	my $dbh = DBI->connect("dbi:SQLite:dbname=$str_filepath_db","","",{PrintError=>0}) or sub_error_exit("DBI open error : ".$DBI::errstr);
	
	# TBL_ADDRBOOK内のデータ行数を求める
	my $str_sql = "select count(*) from TBL_ADDRBOOK";
	my $sth = $dbh->prepare($str_sql) or sub_error_exit("DBI prepare error : ".$DBI::errstr);
	$sth->execute() or sub_error_exit("DBI execute error : ".$DBI::errstr);

	my @arr = $sth->fetchrow_array();
	print("<p class=\"info\">データベースには  ".$arr[0]." 件のデータが格納されています</p>");
	$sth->finish();
	$dbh->disconnect;
}


sub sub_list_db{
	my $dbh = DBI->connect("dbi:SQLite:dbname=$str_filepath_db","","",{PrintError=>0}) or sub_error_exit("DBI open error : ".$DBI::errstr);
	
	print("<h1>List Database (データベース内のデータ一覧)</h1>\n");

	# TBL_ADDRBOOKの全データを読み出す
	my $str_sql = "select * from TBL_ADDRBOOK";
	my $sth = $dbh->prepare($str_sql) or sub_error_exit("DBI prepare error : ".$DBI::errstr);
	$sth->execute() or sub_error_exit("DBI execute error : ".$DBI::errstr);
	print("<ul>\n");
	while(my @arr = $sth->fetchrow_array()){
		for(my $i=0; $i<=$#arr; $i++){
			if(defined($arr[$i]) && length($arr[$i])>0){ $arr[$i] = sub_conv_to_flagged_utf8($arr[$i], 'utf8'); }
		}
		print("<li class=\"person\"><a class=\"person\">");
		for( $i=0; $i<=$#arr; $i++){
			print((defined($arr[$i])?$arr[$i]:'').",");
		}
		print("</a></li>\n");
	}
	print("</ul>\n");
	$sth->finish();
	$dbh->disconnect;

}

# DBをバックアップ
sub sub_backup_db{
	my $q_ref = shift;
	
	my $str_filepath_backup;
	my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
	$str_filepath_backup = sprintf("%s/%04d_%02d_%02d_%02d_%02d_%02d.csv", $str_dir_backup, $year+1900, $mon+1, $mday, $hour, $min, $sec); 

	print("<h1>Backup Database (データベースのバックアップ)</h1>\n");

	if( -e $str_filepath_backup ){ sub_error_exit("バックアップファイル ".$str_filepath_backup." がすでに存在します"); }

	sub_download_csv(\$q, 'thunderbird', $str_filepath_backup);

	print("<p class=\"info\">$str_filepath_backup にバックアップ完了</p>\n");

}

# CSVファイルアップロードのためのファイル選択画面
sub sub_disp_upload_filepick{
	print("<h1>Upload CSV datafile (CSVファイルのアップロード)</h1>\n".
		"<p>Thunderbirdアドレス帳からエクスポートしたCSVファイルを Databaseに取り込みます</p>\n".
		"<p>&nbsp;</p>\n".
		"<form method=\"post\" action=\"$str_this_script\" enctype=\"multipart/form-data\">\n".
		"CSVファイル\n".
		"<p><input type=\"file\" name=\"uploadfile\" value=\"\" size=\"20\" />\n".
		"<input type=\"submit\" value=\"アップロード\" /></p>\n".
		"<p><input type=\"checkbox\" name=\"purge_data\" value=\"purge\" checked=\"checked\" />DB初期化後に新規追加する</p>".
		"</form>\n");
}

sub sub_upload_csv{
	my $q_ref = shift;
	my $flag_purge_data = shift;

	print("<h1>Upload CSV datafile (CSVファイルのアップロード)</h1>\n".
		"<p>アップロードファイルを一時保存中 ...</p>\n");
	my $str_filename = $$q_ref->param('uploadfile');
	print("<p>アップロードされたファイル = ".$str_filename."</p>\n");

	my $fh = $$q_ref->upload('uploadfile');
	my $str_temp_filepath = $$q_ref->tmpFileName($fh);

	print("<p>ファイルアップロード処理中 ...(".$str_temp_filepath.")</p>\n");

	File::Copy::move($str_temp_filepath, $str_filepath_csv_tmp) or sub_error_exit("Error : 一時ファイル ".$str_filepath_csv_tmp." の移動処理失敗");

	close($fh);

	unless( -f $str_filepath_csv_tmp ){ sub_error_exit("Error : 一時ファイル ".$str_filepath_csv_tmp." の存在が検知できない"); }


	print("<p>Databaseを検証中 ...</p>\n");
	if($flag_purge_data == 1){
		print("<p>既存テーブルを削除中 ...</p>\n");
		sub_purge_db_table();
		sub_make_new_table();
	}


	print("<p>Databaseに登録中 ...</p>\n");
	sub_add_from_csv();
	
	unlink($str_filepath_csv_tmp);

	print "<p class=\"ok\">データの取り込み完了</p>\n";
	
}

# テーブルの新規作成
sub sub_make_new_table {
	my $q_ref = shift;

	my $dbh = DBI->connect("dbi:SQLite:dbname=$str_filepath_db","","",{PrintError=>0}) or sub_error_exit_with_htmlstart($q_ref, "DBI open error : ".$DBI::errstr);
	
	# TABLEが存在するかクエリを行う
	my $str_sql = "select count(*) from sqlite_master where type='table' and name='TBL_ADDRBOOK'";
	my $sth = $dbh->prepare($str_sql) or sub_error_exit_with_htmlstart($q_ref, "DBI prepare error : ".$DBI::errstr);
	$sth->execute() or sub_error_exit_($q_ref, "DBI execute error : ".$DBI::errstr);
	my @arr = $sth->fetchrow_array();
	if($arr[0] == 1){
		# テーブル数が1の時は、テーブルが存在するためサブルーチンを終了する
		$sth->finish();
		$dbh->disconnect;
		return;
	}
	$sth->finish();


	# テーブルを新規作成する
	$str_sql = "CREATE TABLE TBL_ADDRBOOK(".
			"idx INTEGER PRIMARY KEY AUTOINCREMENT";

	open(FH, '<'.$str_filepath_datastruct) or sub_error_exit_with_htmlstart($q_ref, "File (datastruct) open error");
	while(<FH>){
		chomp;
		s/\,\;\"\'//g;
		if(length($_)>=1){ $str_sql = $str_sql . "," . $_ . " TEXT"; }
	}
	close(FH);
	$str_sql .= ")";
		
	$sth = $dbh->prepare($str_sql) or sub_error_exit_with_htmlstart($q_ref, "DBI prepare error : ".$DBI::errstr);
	$sth->execute()  or sub_error_exit_with_htmlstart($q_ref, "DBI execute error : ".$DBI::errstr);
	$sth->finish();
	$dbh->disconnect;
		
}

# DBのTBL_ADDRBOOKテーブルのデータを空にする
sub sub_purge_db_table{
	my $dbh = DBI->connect("dbi:SQLite:dbname=$str_filepath_db","","",{PrintError=>0}) or sub_error_exit("DBI open error : ".$DBI::errstr);

	# TABLEが存在するかクエリを行う
	my $str_sql = "select count(*) from sqlite_master where type='table' and name='TBL_ADDRBOOK'";
	my $sth = $dbh->prepare($str_sql) or sub_error_exit("DBI prepare error : ".$DBI::errstr);
	$sth->execute() or sub_error_exit("DBI execute error : ".$DBI::errstr);
	my @arr = $sth->fetchrow_array();
	if($arr[0] == 0){
		# テーブル数が0の時は、テーブルが存在しないためサブルーチンを終了する
		$sth->finish();
		$dbh->disconnect;
		return;
	}
	$sth->finish();
	$sth = undef;

	# テーブルを削除する
	$str_sql = "drop table 'TBL_ADDRBOOK'";
	$sth = $dbh->prepare($str_sql) or sub_error_exit("DBI prepare error : ".$DBI::errstr);
	$sth->execute() or sub_error_exit("DBI execute error : ".$DBI::errstr);
	$sth->finish();
	$dbh->disconnect;
}

# thunderbird形式CSVを読み込んで、DBに追加する
sub sub_add_from_csv {
	my %hash_coord;

	# sqliteカラム名とThunderbirdカラム名の対応関係のハッシュを作成
	open(FH, '<'.$str_filepath_datastruct_tb) or sub_error_exit("File (datastruct_tb) open error");
	while(<FH>){
		chomp;
		my $str_line = sub_conv_to_flagged_utf8($_);
		my @arr = split(/\,/, $str_line);
		if($#arr != 1){ next; }
		$hash_coord{$arr[0]} = $arr[1];		# 例 $hash{'name_family'} = '姓'
	}
	close(FH);

	# CSVファイルの文字エンコードを得る（ファイル全体からエンコード形式を推測する）
	my $enc = sub_get_encode_of_file($str_filepath_csv_tmp);
	print("<p>入力CSVの文字コード検出 : ".$enc."</p>\n");

	# CSVファイルを読み込んで、1行ずつ処理（DB登録）
	if(open(FH_IN, '<'.$str_filepath_csv_tmp)){

		my $csv = Text::CSV_XS->new({binary=>1});

		# CSVファイル1行目はカラム名の列挙
		my $str_line = <FH_IN>;
		$str_line = sub_conv_to_flagged_utf8($str_line, $enc);
		$csv->parse($str_line);
		my @arr_keyname = $csv->fields();

		my $dbh = DBI->connect("dbi:SQLite:dbname=$str_filepath_db","","",{PrintError=>0}) or sub_error_exit("DBI open error : ".$DBI::errstr);
		# SQL文 "INSERT INTO TBL_ADDRBOOK ('name_family','name_given') VALUES (?,?)"
		my $str_sql = "INSERT INTO TBL_ADDRBOOK (";
		my @arr_keys = keys(%hash_coord);
		for(my $i=0; $i<=$#arr_keys; $i++){
			if($arr_keys[$i] eq '-'){ next; }	# カラム名が '-' はDBに存在しないためスキップ
			$str_sql .= "'".$arr_keys[$i]."',";
		}
		$str_sql = substr($str_sql, 0, length($str_sql)-1);		# 末尾の "," を除去
		$str_sql .= ') VALUES (';
		for(my $i=0; $i<=$#arr_keys; $i++){
			if($arr_keys[$i] eq '-'){ next; }	# カラム名が '-' はDBに存在しないためスキップ
			$str_sql .= '?,';
		}
		$str_sql = substr($str_sql, 0, length($str_sql)-1);		# 末尾の "," を除去
		$str_sql .= ')';
		
		my $sth = $dbh->prepare($str_sql) or sub_error_exit("DBI prepare error : ".$DBI::errstr);

		# CSV各行を INSERT 文でDBに登録
		my $n_count = 0;
		while(<FH_IN>)
		{
			my $str_line = $_;
			if($str_line eq ''){ next; }
			$str_line = sub_conv_to_flagged_utf8($str_line, $enc);
			$csv->parse($str_line) or next;
			my @arr_fields = $csv->fields();
			if($#arr_fields < 1 || $#arr_fields > $#arr_keyname){ next; }		# 要素数がおかしいときはスキップ

			my %hash_elem;
			for(my $i=0; $i<=$#arr_fields; $i++){
				$hash_elem{$arr_keyname[$i]} = $arr_fields[$i];
			}

			my @arr_values;
			for(my $i=0; $i<=$#arr_keys; $i++){
				if($arr_keys[$i] eq '-'){ next; }	# カラム名が '-' はDBに存在しないためスキップ
				push(@arr_values, $hash_elem{$hash_coord{$arr_keys[$i]}});
			}
			if($sth){ $sth->execute(@arr_values);}
			$n_count++;
		}

		if($sth){ $sth->finish();}
		$dbh->disconnect;

		close(FH_IN);
		
		print("<p class=\"info\">".$n_count." 件のデータを登録しました</p>\n");

	}
	else{
		sub_error_exit("Error : 一時ファイルを開くことができません");
	}

}


# ダウンロード メニューの表示
sub sub_disp_download{
	print("<h1>Download CSV datafile (CSVファイルのダウンロード)</h1>\n");
	
	print("<ul>\n<li><a href=\"".$str_this_script."?mode=download_thunderbird\">Thunderbird形式CSVをダウンロード</a></li>\n".
		"<li><a href=\"".$str_this_script."?mode=download_gmail\">GMail連絡先形式CSVをダウンロード</a></li>\n</ul>\n");
}

# CSVのダウンロード
sub sub_download_csv{
	my $q_ref = shift;
	my $csv_mode = shift;	# 出力形式（thunderbird,gmail）
	my $output_mode = shift;	# 出力モード（download, $backup_filepath）

	my $str_filepath_datastruct_sel;
	my $str_filepath_backup = $output_mode;		# バックアップ時はファイル名
	 
	my @arr_keys;
	my @arr_label;

	if($csv_mode eq 'thunderbird'){ $str_filepath_datastruct_sel = $str_filepath_datastruct_tb; }
	if($csv_mode eq 'gmail'){ $str_filepath_datastruct_sel = $str_filepath_datastruct_gm; }

	
	# ダウンロード用のヘッダを出力
	if($output_mode eq 'download'){
		print $$q_ref->header(-type=>'application/octet-stream', -attachment=>'test.csv');
		# print qq{Content-Disposition: attachment; filename="filename.csv"\n};
		# print qq{Content-type: application/octet-stream\n\n};
	}

	# sqliteカラム名とThunderbirdカラム名の対応関係の配列を作成
	open(FH, '<'.$str_filepath_datastruct_sel) or sub_error_exit("File (datastruct) open error");
	while(<FH>){
		chomp;
		my $str_line = sub_conv_to_flagged_utf8($_);
		my @arr = split(/\,/, $str_line);
		if($#arr != 1){ next; }
		push(@arr_keys, $arr[0]);	# ('name_family','name_given'...)
		push(@arr_label, $arr[1]);	# ('姓','名',...）
	}
	close(FH);


	my $dbh = DBI->connect("dbi:SQLite:dbname=$str_filepath_db","","",{PrintError=>0}) or sub_error_exit("DBI open error : ".$DBI::errstr);

	# SQL文 "SELECT 'name_family','name_given' FROM TBL_ADDRBOOK"
	my $str_sql = "select ";
	for(my $i=0; $i<=$#arr_keys; $i++){
		if($arr_keys[$i] eq '-'){ $str_sql .= "'',"; }	# カラム名が '-' はDBのnullカラム（''）を出力
		else{ $str_sql .= $arr_keys[$i].","; }
	}
	$str_sql = substr($str_sql, 0, length($str_sql)-1);		# 末尾の "," を除去
	$str_sql .= " from TBL_ADDRBOOK";

	my $sth = $dbh->prepare($str_sql) or sub_error_exit("DBI prepare error : ".$DBI::errstr);
	$sth->execute() or sub_error_exit("DBI execute error : ".$DBI::errstr);

	if($output_mode ne 'download'){
		open(FH, '>'.$str_filepath_backup) or sub_error_exit("バックアップファイル ".$str_filepath_backup." に書き込めません");
	}
	
	# CSV出力開始
	for(my $i=0; $i<=$#arr_label; $i++){
		if($output_mode eq 'download'){ print($arr_label[$i].","); }
		else{ print(FH $arr_label[$i].","); }
	}
	if($output_mode eq 'download'){ print("\n"); }
	else{ print(FH "\n"); }

	my $csv = Text::CSV_XS->new({binary=>1});

	while(my @arr = $sth->fetchrow_array()){
		for(my $i=0; $i<=$#arr; $i++){
			if(defined($arr[$i]) && length($arr[$i])>0){ $arr[$i] = sub_conv_to_flagged_utf8($arr[$i], 'utf8'); }
		}
		$csv->combine(@arr);
		if($output_mode eq 'download'){ print($csv->string()."\n"); }
		else{ print(FH $csv->string()."\n"); }
	}

	if($output_mode ne 'download'){ close(FH); }


	$sth->finish();
	$dbh->disconnect;

	
}

# リストアのファイル選択画面を表示する
sub sub_disp_restore_select{
	print("<h1>Select restore target file (データベース復元もとの選択)</h1>\n");
	
	my @arr_filelist = glob($str_dir_backup.'/*.csv');
	
	print("<ul>\n");
	foreach(@arr_filelist){
		print("<li><a href=\"".$str_this_script."?mode=restore&amp;file=".basename($_)."\">".$_."</a></li>\n");
	}
	print("</ul>\n");
}

# データベースを指定されたファイルでリストアする
sub sub_restore{
	my $str_filepath_backup = shift;
	my $flag_purge_data = 1;

	print("<h1>Restore database (データベースの復元)</h1>\n");
	
	defined($str_filepath_backup) or sub_error_exit("Error : 復元元ファイル名が指定されていません");
	$str_filepath_backup = $str_dir_backup . '/' . $str_filepath_backup;
	unless( -f $str_filepath_backup){ sub_error_exit("Error : 復元元ファイル".$str_filepath_backup."が存在しません"); }

	print("<p>復元元ファイル : ".$str_filepath_backup."</p>\n");

	File::Copy::copy($str_filepath_backup, $str_filepath_csv_tmp) or sub_error_exit("Restore File move error");


	print("<p>Databaseを検証中 ...</p>\n");
	if($flag_purge_data == 1){
		print("<p>既存テーブルを削除中 ...</p>\n");
		sub_purge_db_table();
		sub_make_new_table();
	}


	print("<p>Databaseに登録中 ...</p>\n");
	sub_add_from_csv();
	
	unlink($str_filepath_csv_tmp);

	print "<p class=\"ok\">データの取り込み完了</p>\n";

}

# 任意の文字コードの文字列を、UTF-8フラグ付きのUTF-8に変換する
sub sub_conv_to_flagged_utf8{
	my $str = shift;
	my $enc_force = undef;
	if(@_ >= 1){ $enc_force = shift; }		# デコーダの強制指定
	
	# デコーダが強制的に指定された場合
	if(defined($enc_force)){
		if(ref($enc_force)){
			$str = $enc_force->decode($str);
			return($str);
		}
		elsif($enc_force ne '')
		{
			$str = Encode::decode($enc_force, $str);
		}
	}

	my $enc = Encode::Guess->guess($str);	# 文字列のエンコードの判定

	unless(ref($enc)){
		# エンコード形式が2個以上帰ってきた場合 （shiftjis or utf8）
		my @arr_encodes = split(/ /, $enc);
		if(grep(/^$flag_charcode/, @arr_encodes) >= 1){
			# $flag_charcode と同じエンコードが検出されたら、それを優先する
			$str = Encode::decode($flag_charcode, $str);
		}
		elsif(lc($arr_encodes[0]) eq 'shiftjis' || lc($arr_encodes[0]) eq 'euc-jp' || 
			lc($arr_encodes[0]) eq 'utf8' || lc($arr_encodes[0]) eq 'us-ascii'){
			# 最初の候補でデコードする
			$str = Encode::decode($arr_encodes[0], $str);
		}
	}
	else{
		# UTF-8でUTF-8フラグが立っている時以外は、変換を行う
		unless(ref($enc) eq 'Encode::utf8' && utf8::is_utf8($str) == 1){
			$str = $enc->decode($str);
		}
	}

	return($str);
}


# 任意の文字コードの文字列を、UTF-8フラグ無しのUTF-8に変換する
sub sub_conv_to_unflagged_utf8{
	my $str = shift;

	# いったん、フラグ付きのUTF-8に変換
	$str = sub_conv_to_flagged_utf8($str);

	return(Encode::encode('utf8', $str));
}


# UTF8から現在のOSの文字コードに変換する
sub sub_conv_to_local_charset{
	my $str = shift;

	# UTF8から、指定された（OSの）文字コードに変換する
	$str = Encode::encode($flag_charcode, $str);
	
	return($str);
}


# 引数で与えられたファイルの エンコードオブジェクト Encode::encode を返す
sub sub_get_encode_of_file{
	my $fname = shift;		# 解析するファイル名

	# ファイルを一気に読み込む
	open(FH, "<".sub_conv_to_local_charset($fname));
	my @arr = <FH>;
	close(FH);
	my $str = join('', @arr);		# 配列を結合して、一つの文字列に

	my $enc = Encode::Guess->guess($str);	# 文字列のエンコードの判定

	# エンコード形式の表示（デバッグ用）
	print("Automatick encode ");
	if(ref($enc) eq 'Encode::utf8'){ print("detect : utf8\n"); }
	elsif(ref($enc) eq 'Encode::Unicode'){
		print("detect : ".$$enc{'Name'}."\n");
	}
	elsif(ref($enc) eq 'Encode::XS'){
		print("detect : ".$enc->mime_name()."\n");
	}
	elsif(ref($enc) eq 'Encode::JP::JIS7'){
		print("detect : ".$$enc{'Name'}."\n");
	}
	else{
		# 二つ以上のエンコードが推定される場合は、$encに文字列が返る
		print("unknown (".$enc.")\n");
	}

	# エンコード形式が2個以上帰ってきた場合 （例：shiftjis or utf8）でテクと失敗と扱う
	unless(ref($enc)){
		$enc = '';
	}

	# ファイルがHTMLの場合 Content-Type から判定する
	if(lc($fname) =~ m/html$/ || lc($fname) =~ m/htm$/){
		my $parser = HTML::HeadParser->new();
		unless($parser->parse($str)){
			my $content_enc = $parser->header('content-type');
			if(defined($content_enc) && $content_enc ne '' && lc($content_enc) =~ m/text\/html/ ){
				if(lc($content_enc) =~ m/utf-8/){ $enc = 'utf8'; }
				elsif(lc($content_enc) =~ m/shift_jis/){ $enc = 'shiftjis'; }
				elsif(lc($content_enc) =~ m/euc-jp/){ $enc = 'euc-jp'; }
				
				print("HTML Content-Type detect : ". $content_enc ." (is overrided)\n");
				$enc = $content_enc;
			}
		}
	}

	return($enc);
}
