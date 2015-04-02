# coding: utf-8
import re
from thread import start_new_thread
from logger import Logger


class Client:

    tous = []
    discussionOuverte = [] # Qui est autorisé à parler avec qui - 0: client, 1: client


    def __init__(self, pconn):

        self.conn = pconn;
        self.nom = None;
        self.actif = True
        self.discussionEnAttente = []
        start_new_thread(self.wait4name, ())

    def initco(self):
        clientList = ""
        for c in Client.tous:
            if c.actif:
                clientList += " " + c.nom
                c.conn.sendall("HAS_JOIN "+ self.nom)

        clientListAway = ""
        for c in Client.tous:
            if not c.actif:
                clientList += " " + c.nom
                c.conn.sendall("HAS_JOIN "+ self.nom)

        Client.tous.append(self)

        self.conn.sendall("CHANNEL_JOINED_AS " + self.nom)
        self.conn.sendall("USERLIST" + clientList)
        self.conn.sendall("USERLISTAWAY" + clientListAway)
        start_new_thread(self.client_thread, ())

    def wait4name(self):
        disconnected = False

        while True:
            try:
                tmpData = self.conn.recv(1024)
            except:
                disconnected = True
                break
            if not tmpData:
                disconnected = True
                break

            data = ' '.join(tmpData.split())
            commande = data.split(" ")[0]
            # todo message de retour + utilisateur existant
            if commande == "/newname":
                name = data[len(commande)+1:]
                if re.match("^\w{3,15}$", name):
                    self.nom = name
                    self.initco()
                    break

        if disconnected:
            self.conn.close()

    def client_thread(self):

        # ON ECOUTE CHAQUE CLIENT
        while True:
            try:
                tmpData = self.conn.recv(1024)
            except:
                break
            if not tmpData: break
            data = ' '.join(tmpData.split())
            Logger.logger.info(self.nom +" :: " +data)

            if data == "/quit":
                self.conn.sendall("SUCCESSFUL_LOGOUT")
                break #on ferme le socket

            if data[0] == '/': #c'est une commande spéciale
                reponse = self.getReply(data[1:])
            else: #c'est un message à envoyer à tous les clients actifs
                for c in Client.tous:
                    if c!=self: c.conn.sendall("NEW_MSG "+ self.nom + " " + data)
                reponse = "SUCCESSFUL_MESSAGE_SENDED"

            if reponse:
                self.conn.sendall(reponse)


        #EXIT
        Client.tous.remove(self)
        for c in Client.tous:
            c.conn.sendall("HAS_LEFT "+ self.nom)
        self.conn.close()



    def getReply(self, data):
        commande = data.split(" ")[0]
        argument = data[len(commande)+1:]
        if(commande == "name"):
            if re.match("^\w{3,15}$", argument):
                if Client.getByName(argument): return "ERR_NICKNAME_ALREADY_USED"
                ancienNom = self.nom
                self.nom = argument
                for c in Client.tous:
                    if c != self:
                        c.conn.sendall("NAME_CHANGED "+ancienNom+" "+self.nom)
                return "SUCC_NICKNAME_CHANGED_TO " + self.nom
            return "ERR_INVALID_NICKNAME"

        if(commande == "pm"):
            dest = Client.getByName(argument.split(" ")[0])
            if dest:
                if not Client.isDiscussionOuverte(dest, self): return "ERR_CONV_NOT_ALLOWED"
                dest.conn.sendall("NEW_PM "+ self.nom + " " + argument[len(dest.nom)+1:])
                return "SUCC_PM_SENDED " +  data.split(" ")[1] + " " +  data.split(" ")[2]
            return "ERR_DEST_NOT_FOUND"

        if(commande == "askpm"):
            dest = Client.getByName(argument.split(" ")[0])
            if dest:
                d = dest.getDiscussionEnAttenteFrom(self)
                if not d:
                    dest.discussionEnAttente.append(self)
                    dest.conn.sendall("ASKING_FOR_PM " + self.nom)
                    return "SUCCESSFUL_ASKED"
                return "ERR_ALREADY_ASKED"
            return "ERR_DEST_NOT_FOUND"

        if(commande == "acceptpm"):
            dest = Client.getByName(argument.split(" ")[0])
            # todo les 2 on fait un accept
            if dest:
                d = self.getDiscussionEnAttenteFrom(dest)
                if d:
                    self.discussionEnAttente.remove(dest)
                    Client.discussionOuverte.append([self, dest])
                    return "SUCCESSFUL_ACCEPTED"
                return "ERR_NO_INVITATION_FOUND"
            return "ERR_DEST_NOT_FOUND"

        if(commande == "rejectpm"):
            dest = Client.getByName(argument.split(" ")[0])
            if dest:
                d = self.getDiscussionEnAttenteFrom(dest)
                if d:
                    self.discussionEnAttente.remove(dest)
                    # todo arreter une connexion deja ouverte
                    return "SUCCESSFUL_REFUSED"
                return "ERR_NO_INVITATION_FOUND"
            return "ERR_DEST_NOT_FOUND"

        if(commande == "enable"):
            self.actif = True
            for c in Client.tous:
                if c != self:
                    c.conn.sendall("IS_NOW_ENABLE "+self.nom)
            return "SUCC_ENABLED"
        if(commande == "disable"):
            self.actif = False
            for c in Client.tous:
                if c != self:
                    c.conn.sendall("IS_NOW_DISABLE "+self.nom)
            return "SUCC_DISABLED"

        if(commande == "pmfile"):

            dest = Client.getByName(argument.split(" ")[0])
            if dest:
                dest.conn.sendall("NEW_FILE_REQUEST "+self.nom)
                return "SUCC_PMFILE"
            return "ERR_DEST_NOT_FOUND"








        return "COMMAND_NOT_FOUND"

    @staticmethod
    def getByName(nom):
        for c in Client.tous:
            if c.nom == nom: return c
        return None

    @staticmethod
    def genererNom():
        cpt=1
        while Client.getByName("Anonyme"+str(cpt)):
            cpt = cpt + 1
        return "Anonyme"+str(cpt)

    @staticmethod
    def isDiscussionOuverte(c1, c2):
        for ac in Client.discussionOuverte:
            if (ac[0] == c1 and ac[1] == c2) or (ac[1] == c1 and ac[0] == c2) :
                return True
        return False


    def getDiscussionEnAttenteFrom(self, c1):
        for ac in self.discussionEnAttente:
            if (ac == c1):
                return ac
        return None